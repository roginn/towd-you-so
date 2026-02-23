import json
import logging
import uuid

from agent.llm import call_llm
from db.database import get_db
from db.models import EntryKind
from db.repository import append_entry, list_memories
from interface.models import entry_to_wire
from tools import TOOL_DEFINITIONS, TOOL_REGISTRY
from worker.registry import push_to_client

logger = logging.getLogger(__name__)

MEMORY_MANAGER_TOOLS = [
    "memory_create",
    "memory_update",
    "memory_delete",
    "memory_list",
]

SYSTEM_PROMPT = (
    "You are a memory manager for a parking assistant app. "
    "You receive user messages that may contain parking-relevant personal info "
    "(city, permits, vehicle type, work schedule, etc.).\n\n"
    "Your job is to decide whether to create, update, or delete memories. "
    "You have access to the current memories and CRUD tools.\n\n"
    "Guidelines:\n"
    "- Avoid duplicates: if a memory already covers this info, update it instead of creating a new one.\n"
    "- Keep memories concise, factual, and parking-relevant.\n"
    "- Each memory should be a single fact, e.g. 'User lives in San Francisco'.\n"
    "- If the user corrects previous info (e.g. 'I moved to LA'), update the existing memory.\n"
    "- Only store info that would help answer future parking questions.\n"
    "- Do NOT store transient info like 'user asked about parking on Main St today'.\n"
    "- When done, respond with a brief summary of what you did."
)


def _get_tools() -> list[dict]:
    return [d for d in TOOL_DEFINITIONS if d["function"]["name"] in MEMORY_MANAGER_TOOLS]


async def run_agent(relevant_messages: list[str], session_id: uuid.UUID | None = None) -> dict:
    """Run the memory manager subagent with LLM reasoning loop."""
    # Load existing memories
    async with get_db() as db:
        existing = await list_memories(db)

    memories_text = "\n".join(
        f"- [{m.id}] {m.content}" for m in existing
    ) or "(no existing memories)"

    user_content = (
        f"Existing memories:\n{memories_text}\n\n"
        f"New user messages to process:\n"
        + "\n".join(f'- "{msg}"' for msg in relevant_messages)
    )

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]
    tools = _get_tools()
    actions_taken = []

    for _turn in range(3):
        response = await call_llm(messages, tools=tools)

        if response.tool_calls:
            # Append function_call items and execute each tool
            for tc in response.tool_calls:
                messages.append({
                    "type": "function_call",
                    "name": tc.tool_name,
                    "arguments": json.dumps(tc.arguments),
                    "call_id": tc.call_id,
                })

                # Write TOOL_CALL entry to DB
                if session_id:
                    tool_call_data = {
                        "call_id": tc.call_id,
                        "tool_name": tc.tool_name,
                        "arguments": tc.arguments,
                        "agent_name": "memory_manager",
                    }
                    async with get_db() as db:
                        tc_entry = await append_entry(db, session_id, EntryKind.TOOL_CALL, tool_call_data)
                    await push_to_client(session_id, entry_to_wire(tc_entry))

                module = TOOL_REGISTRY.get(tc.tool_name)
                if module:
                    result = await module.run(**tc.arguments)
                    actions_taken.append(f"{tc.tool_name}: {json.dumps(result)}")
                else:
                    result = {"error": f"Unknown tool: {tc.tool_name}"}

                # Write TOOL_RESULT entry to DB
                if session_id:
                    tool_result_data = {
                        "call_id": tc.call_id,
                        "result": result,
                    }
                    async with get_db() as db:
                        tr_entry = await append_entry(db, session_id, EntryKind.TOOL_RESULT, tool_result_data)
                    await push_to_client(session_id, entry_to_wire(tr_entry))

                messages.append({
                    "type": "function_call_output",
                    "call_id": tc.call_id,
                    "output": json.dumps(result),
                })
        else:
            # LLM responded with text — we're done
            summary = response.content or "No changes made."
            return {"summary": summary, "actions": actions_taken}

    return {"summary": "Memory manager completed (max turns reached).", "actions": actions_taken}
