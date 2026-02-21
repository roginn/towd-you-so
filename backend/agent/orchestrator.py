import json
import logging
import uuid

from openai import AsyncOpenAI

from conductor.registry import enqueue_entry, push_to_client
from config import settings
from tools import TOOL_DEFINITIONS
from db.database import get_db
from db.models import EntryKind
from db.repository import append_entry, get_session_entries
from interface.models import entry_to_wire

logger = logging.getLogger(__name__)

openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

SYSTEM_PROMPT = (
    "You are Tow'd You So, an AI parking sign assistant. "
    "Users send you photos of parking signs and ask whether they can park. "
    "Use the provided tools to read the sign and determine the current time, "
    "then give a clear yes/no/conditional answer with a brief explanation."
)


async def start_session(
    session_id: uuid.UUID, content: str, image_url: str | None = None
) -> None:
    """Called when a user sends a message. Writes user_message entry and kicks off the agent loop."""
    data: dict = {"content": content}
    if image_url:
        data["image_url"] = image_url

    async with get_db() as db:
        entry = await append_entry(db, session_id, EntryKind.USER_MESSAGE, data)

    await push_to_client(session_id, entry_to_wire(entry))
    await continue_session(session_id)


async def continue_session(session_id: uuid.UUID) -> None:
    """Load all entries, build LLM messages, call LLM, write resulting entries."""
    async with get_db() as db:
        entries = await get_session_entries(db, session_id)

    messages = _build_llm_messages(entries)

    try:
        response = await openai_client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=messages,
            tools=TOOL_DEFINITIONS,
        )
    except Exception:
        logger.exception("LLM call failed for session %s", session_id)
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

    choice = response.choices[0]

    if choice.finish_reason == "tool_calls" or choice.message.tool_calls:
        # LLM wants to call tools
        for tc in choice.message.tool_calls:
            tool_data = {
                "call_id": tc.id,
                "tool_name": tc.function.name,
                "arguments": json.loads(tc.function.arguments),
            }
            async with get_db() as db:
                entry = await append_entry(
                    db, session_id, EntryKind.TOOL_CALL, tool_data
                )
            await push_to_client(session_id, entry_to_wire(entry))
            enqueue_entry(session_id, entry.id)
    else:
        # LLM returned a final response
        content = choice.message.content or ""
        async with get_db() as db:
            entry = await append_entry(
                db,
                session_id,
                EntryKind.ASSISTANT_MESSAGE,
                {"content": content},
            )
        await push_to_client(session_id, entry_to_wire(entry))
        await push_to_client(session_id, {"type": "turn_complete"})


def _build_llm_messages(entries: list) -> list[dict]:
    """Map Entry rows to OpenAI chat message format per PRD §2.3.6."""
    messages: list[dict] = [{"role": "system", "content": SYSTEM_PROMPT}]

    for entry in entries:
        kind = entry.kind
        data = entry.data

        if kind == EntryKind.USER_MESSAGE:
            content_parts = []
            if data.get("content"):
                content_parts.append({"type": "text", "text": data["content"]})
            if data.get("image_url"):
                content_parts.append(
                    {"type": "image_url", "image_url": {"url": data["image_url"]}}
                )
            messages.append({"role": "user", "content": content_parts})

        elif kind == EntryKind.ASSISTANT_MESSAGE:
            messages.append({"role": "assistant", "content": data["content"]})

        elif kind == EntryKind.TOOL_CALL:
            # Represent as an assistant message with tool_calls
            messages.append(
                {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": data["call_id"],
                            "type": "function",
                            "function": {
                                "name": data["tool_name"],
                                "arguments": json.dumps(data["arguments"]),
                            },
                        }
                    ],
                }
            )

        elif kind == EntryKind.TOOL_RESULT:
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": data["call_id"],
                    "content": json.dumps(data["result"]),
                }
            )

        # reasoning, sub_agent_call, sub_agent_result are excluded

    return messages
