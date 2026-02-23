import asyncio
import logging
import uuid

from agent.orchestrator import continue_session
from worker.registry import mark_batch_done, push_to_client
from worker.tool_executor import execute_tool
from db.database import get_db
from db.models import EntryKind, EntryStatus
from db.repository import append_entry, get_entry, mark_entry_status
from interface.models import entry_to_wire
from tools._registry import SUB_AGENT_TOOLS

logger = logging.getLogger(__name__)


async def run_worker(session_id: uuid.UUID, queue: asyncio.Queue) -> None:
    """Per-session async loop. Processes pending executable entries."""
    while True:
        entry_id: uuid.UUID = await queue.get()
        try:
            await _process_entry(session_id, entry_id)
        except Exception:
            logger.exception("Worker error processing entry %s", entry_id)


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
            tool_name = entry.data["tool_name"]
            call_id = entry.data["call_id"]
            arguments = entry.data.get("arguments", {})
            agent_name = SUB_AGENT_TOOLS.get(tool_name)

            # If this is a sub-agent tool, create a SUB_AGENT_CALL entry
            sub_agent_call_entry = None
            if agent_name:
                sub_agent_call_data = {"call_id": call_id, "agent_name": agent_name}
                async with get_db() as db:
                    sub_agent_call_entry = await append_entry(
                        db, session_id, EntryKind.SUB_AGENT_CALL, sub_agent_call_data
                    )
                await push_to_client(session_id, entry_to_wire(sub_agent_call_entry))

            # Pass session_id to sub-agent tools so they can write their own entries
            if agent_name:
                result = await execute_tool(
                    tool_name, {**arguments, "session_id": session_id, "call_id": call_id}
                )
            else:
                result = await execute_tool(tool_name, arguments)

            result_kind = EntryKind.TOOL_RESULT
            result_data = {"call_id": call_id, "result": result}

            # If this is a sub-agent tool, create a SUB_AGENT_RESULT entry
            if agent_name and sub_agent_call_entry:
                sub_agent_result_data = {"call_id": call_id, "result": result}
                async with get_db() as db:
                    sub_agent_result_entry = await append_entry(
                        db, session_id, EntryKind.SUB_AGENT_RESULT, sub_agent_result_data
                    )
                    await mark_entry_status(db, sub_agent_call_entry.id, EntryStatus.DONE)
                await push_to_client(session_id, entry_to_wire(sub_agent_result_entry))
                await push_to_client(
                    session_id,
                    {"type": "status", "entry_id": str(sub_agent_call_entry.id), "status": "done"},
                )

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

        # Re-trigger orchestrator when all tool calls in this batch are done
        if mark_batch_done(session_id, entry.data["call_id"]):
            asyncio.create_task(continue_session(session_id))

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
            if mark_batch_done(session_id, entry.data["call_id"]):
                asyncio.create_task(continue_session(session_id))
