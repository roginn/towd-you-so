import json
import logging
import uuid

from worker.registry import enqueue_entry, push_to_client, register_batch
from db.database import get_db
from db.models import EntryKind
from db.repository import append_entry, get_session_entries, list_memories
from interface.models import entry_to_wire

from agent.llm import (
    build_llm_messages,
    build_responses_input,
    call_llm,
    call_llm_streaming,
    ContentDelta,
    ReasoningDelta,
    StreamDone,
    ToolCallDelta,
    ToolCallResult,
)
from tools import TOOL_DEFINITIONS

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are Tow'd You So, an AI parking sign assistant. "
    "Users send you photos of parking signs and ask whether they can park. "
    "When you receive a message with an image, call the task_read_parking_sign tool "
    "to extract the sign's rules. Then call get_current_time "
    "to determine the current date, time, and day of week. "
    "Use both results to give a clear yes/no/conditional answer with a brief explanation.\n\n"
    "When the user mentions persistent parking-relevant personal info — such as their city, "
    "neighborhood, parking permits, vehicle type, work schedule, or regular parking habits — "
    "call the store_memory tool with the relevant message text so it can be remembered "
    "for future sessions. Use the existing memories (listed below) to personalize your answers.\n\n"
    "LOCATION FEATURES:\n"
    "- After reading a parking sign, offer to save its location: "
    "'Would you like me to save this parking sign? Just tell me approximately where this picture was taken.'\n"
    "- When the user describes a location (e.g. '20th st between illinois and georgia'), "
    "call task_location with a task like 'Save this parking sign at: <location>' "
    "along with the uploaded_file_id and sign_text from the earlier reading.\n"
    "- When the user asks 'where can I park near X?' or similar, call task_location "
    "with a search task description like 'Search for parking signs near: <location>'.\n"
    "- Default search radius is ~1 mile (1600m). If the user asks to expand, include that in the task.\n"
    "- The location agent returns nearby signs with their rules text — check the current time "
    "against each sign's rules to tell the user which are viable parking options right now."
)

ORCHESTRATOR_TOOLS = [
    "task_read_parking_sign",
    "get_current_time",
    "vision",
    "store_memory",
    "task_location",
]


def _get_tools(names: list[str]) -> list[dict]:
    return [d for d in TOOL_DEFINITIONS if d["function"]["name"] in names]


async def start_session(
    session_id: uuid.UUID,
    content: str,
    uploaded_file_id: uuid.UUID | None = None,
    image_url: str | None = None,
) -> None:
    """Called when a user sends a message. Writes user_message entry and kicks off the agent loop."""
    data: dict = {"content": content}
    if image_url:
        data["image_url"] = image_url

    async with get_db() as db:
        entry = await append_entry(
            db, session_id, EntryKind.USER_MESSAGE, data,
            uploaded_file_id=uploaded_file_id,
        )

    await push_to_client(session_id, entry_to_wire(entry))
    await continue_session(session_id)


async def continue_session(session_id: uuid.UUID) -> None:
    """Load all entries, build LLM messages, stream LLM response, write resulting entries."""
    async with get_db() as db:
        entries = await get_session_entries(db, session_id)
        memories = await list_memories(db)

    # Inject existing memories into system prompt
    prompt = SYSTEM_PROMPT
    if memories:
        memories_text = "\n".join(f"- {m.content}" for m in memories)
        prompt += f"\n\nUser memories:\n{memories_text}"
    else:
        prompt += "\n\nUser memories: (none yet)"

    messages = build_responses_input(entries, prompt)
    tools = _get_tools(ORCHESTRATOR_TOOLS)

    try:
        # Accumulators for the stream
        reasoning_text = ""
        content_text = ""
        # Tool calls accumulator: index -> {call_id, tool_name, arguments_json}
        tool_calls_acc: dict[int, dict] = {}

        async for event in call_llm_streaming(messages, tools=tools):
            if isinstance(event, ReasoningDelta):
                reasoning_text += event.text
                await push_to_client(session_id, {"type": "reasoning_delta", "text": event.text})

            elif isinstance(event, ContentDelta):
                content_text += event.text
                await push_to_client(session_id, {"type": "content_delta", "text": event.text})

            elif isinstance(event, ToolCallDelta):
                tc = tool_calls_acc.setdefault(event.index, {"call_id": "", "tool_name": "", "arguments_json": ""})
                if event.call_id:
                    tc["call_id"] = event.call_id
                if event.tool_name:
                    tc["tool_name"] = event.tool_name
                tc["arguments_json"] += event.arguments_chunk

            elif isinstance(event, StreamDone):
                pass  # handled below

    except Exception:
        logger.exception("LLM streaming failed for session %s", session_id)
        async with get_db() as db:
            entry = await append_entry(
                db,
                session_id,
                EntryKind.ASSISTANT_MESSAGE,
                {"content": "Sorry, I encountered an error processing your request."},
            )
        await push_to_client(session_id, entry_to_wire(entry))
        await push_to_client(session_id, {"type": "turn_complete"})
        return

    # Persist reasoning if received
    if reasoning_text:
        async with get_db() as db:
            entry = await append_entry(
                db, session_id, EntryKind.REASONING, {"content": reasoning_text}
            )
        await push_to_client(session_id, entry_to_wire(entry))

    # Handle tool calls
    if tool_calls_acc:
        tool_call_results = []
        for idx in sorted(tool_calls_acc):
            tc = tool_calls_acc[idx]
            tool_call_results.append(
                ToolCallResult(
                    call_id=tc["call_id"],
                    tool_name=tc["tool_name"],
                    arguments=json.loads(tc["arguments_json"]),
                )
            )

        register_batch(session_id, [tc.call_id for tc in tool_call_results])
        for tc in tool_call_results:
            tool_data = {
                "call_id": tc.call_id,
                "tool_name": tc.tool_name,
                "arguments": tc.arguments,
                "agent_name": "orchestrator",
            }
            async with get_db() as db:
                entry = await append_entry(
                    db, session_id, EntryKind.TOOL_CALL, tool_data
                )
            await push_to_client(session_id, entry_to_wire(entry))
            enqueue_entry(session_id, entry.id)
    elif content_text:
        async with get_db() as db:
            entry = await append_entry(
                db,
                session_id,
                EntryKind.ASSISTANT_MESSAGE,
                {"content": content_text},
            )
        await push_to_client(session_id, entry_to_wire(entry))
        await push_to_client(session_id, {"type": "turn_complete"})
