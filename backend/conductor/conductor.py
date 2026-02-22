import asyncio
import logging
import uuid

from conductor.registry import push_to_client
from conductor.tool_executor import execute_tool
from db.database import get_db
from db.models import EntryKind, EntryStatus
from db.repository import append_entry, get_entry, get_session_entries, mark_entry_status
from interface.models import entry_to_wire

logger = logging.getLogger(__name__)


async def run_conductor(session_id: uuid.UUID, queue: asyncio.Queue) -> None:
    """Per-session async loop. Processes pending executable entries."""
    while True:
        entry_id: uuid.UUID = await queue.get()
        try:
            await _process_entry(session_id, entry_id)
        except Exception:
            logger.exception("Conductor error processing entry %s", entry_id)


async def _process_entry(session_id: uuid.UUID, entry_id: uuid.UUID) -> None:
    # Mark as running
    async with get_db() as db:
        await mark_entry_status(db, entry_id, EntryStatus.RUNNING)
        entry = await get_entry(db, entry_id)

    await push_to_client(
        session_id, {"type": "status", "entry_id": str(entry_id), "status": "running"}
    )

    try:
        if entry.kind == EntryKind.TOOL_CALL:
            result = await execute_tool(
                entry.data["tool_name"], entry.data.get("arguments", {})
            )
            result_kind = EntryKind.TOOL_RESULT
            result_data = {"call_id": entry.data["call_id"], "result": result}

        else:
            return

        # Write result entry and mark original as done
        async with get_db() as db:
            result_entry = await append_entry(db, session_id, result_kind, result_data)
            await mark_entry_status(db, entry_id, EntryStatus.DONE)

        await push_to_client(session_id, entry_to_wire(result_entry))
        await push_to_client(
            session_id,
            {"type": "status", "entry_id": str(entry_id), "status": "done"},
        )

        # Re-trigger orchestrator only when all tool calls have results
        await _maybe_continue(session_id)

    except Exception:
        logger.exception("Failed to process entry %s", entry_id)
        async with get_db() as db:
            await mark_entry_status(db, entry_id, EntryStatus.FAILED)
            # Write an error TOOL_RESULT so the message history stays valid
            # (OpenAI requires every tool_call to have a matching tool response)
            if entry.kind == EntryKind.TOOL_CALL:
                error_entry = await append_entry(
                    db,
                    session_id,
                    EntryKind.TOOL_RESULT,
                    {
                        "call_id": entry.data["call_id"],
                        "result": {"error": "Tool execution failed"},
                    },
                )
                await push_to_client(session_id, entry_to_wire(error_entry))
        await push_to_client(
            session_id,
            {"type": "status", "entry_id": str(entry_id), "status": "failed"},
        )
        if entry.kind == EntryKind.TOOL_CALL:
            await _maybe_continue(session_id)


async def _maybe_continue(session_id: uuid.UUID) -> None:
    """Re-trigger orchestrator only when every tool_call has a matching tool_result."""
    async with get_db() as db:
        entries = await get_session_entries(db, session_id)

    call_ids = {
        e.data["call_id"] for e in entries if e.kind == EntryKind.TOOL_CALL
    }
    result_ids = {
        e.data["call_id"] for e in entries if e.kind == EntryKind.TOOL_RESULT
    }
    if call_ids - result_ids:
        return  # Still waiting on other tool results

    from agent.orchestrator import continue_session

    asyncio.create_task(continue_session(session_id))
