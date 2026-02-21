import logging
import uuid

from conductor.registry import enqueue_entry, push_to_client
from db.database import get_db
from db.models import EntryKind
from db.repository import append_entry, get_session_entries
from interface.models import entry_to_wire

from agent.llm import build_llm_messages, call_llm

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are Tow'd You So, an AI parking sign assistant. "
    "Users send you photos of parking signs and ask whether they can park. "
    "Use the provided tools to read the sign and determine the current time, "
    "then give a clear yes/no/conditional answer with a brief explanation."
)


async def start_session(
    session_id: uuid.UUID,
    content: str,
    image_url: str | None = None,
    uploaded_file_id: uuid.UUID | None = None,
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
    """Load all entries, build LLM messages, call LLM, write resulting entries."""
    async with get_db() as db:
        entries = await get_session_entries(db, session_id)

    messages = build_llm_messages(entries, SYSTEM_PROMPT)

    try:
        llm_response = await call_llm(messages)
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

    if llm_response.tool_calls:
        for tc in llm_response.tool_calls:
            tool_data = {
                "call_id": tc.call_id,
                "tool_name": tc.tool_name,
                "arguments": tc.arguments,
            }
            async with get_db() as db:
                entry = await append_entry(
                    db, session_id, EntryKind.TOOL_CALL, tool_data
                )
            await push_to_client(session_id, entry_to_wire(entry))
            enqueue_entry(session_id, entry.id)
    else:
        async with get_db() as db:
            entry = await append_entry(
                db,
                session_id,
                EntryKind.ASSISTANT_MESSAGE,
                {"content": llm_response.content},
            )
        await push_to_client(session_id, entry_to_wire(entry))
        await push_to_client(session_id, {"type": "turn_complete"})
