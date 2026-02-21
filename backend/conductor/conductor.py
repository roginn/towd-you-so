import asyncio
import logging
import uuid

from conductor.registry import push_to_client
from conductor.tool_executor import execute_tool
from db.database import get_db
from db.models import EntryKind, EntryStatus
from db.repository import append_entry, get_entry, get_session_entries, mark_entry_status
from interface.models import entry_to_wire
from tools.context import ToolContext

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
            # Build ToolContext from session data
            async with get_db() as db:
                entries = await get_session_entries(db, session_id)

            uploaded_file_id = None
            for e in entries:
                if e.kind == EntryKind.USER_MESSAGE and e.uploaded_file_id is not None:
                    uploaded_file_id = e.uploaded_file_id

            context = ToolContext(
                session_id=session_id,
                entries=entries,
                uploaded_file_id=uploaded_file_id,
            )

            result = await execute_tool(
                entry.data["tool_name"], entry.data.get("arguments", {}), context=context
            )
            result_kind = EntryKind.TOOL_RESULT
            result_data = {"call_id": entry.data["call_id"], "result": result}

        elif entry.kind == EntryKind.SUB_AGENT_CALL:
            # Stub: sub-agent execution not yet implemented
            result_kind = EntryKind.SUB_AGENT_RESULT
            result_data = {
                "child_session_id": entry.data.get("child_session_id"),
                "result": {"message": "Sub-agent not yet implemented"},
            }
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

        # Re-trigger orchestrator
        from agent.orchestrator import continue_session

        asyncio.create_task(continue_session(session_id))

    except Exception:
        logger.exception("Failed to process entry %s", entry_id)
        async with get_db() as db:
            await mark_entry_status(db, entry_id, EntryStatus.FAILED)
        await push_to_client(
            session_id,
            {"type": "status", "entry_id": str(entry_id), "status": "failed"},
        )
