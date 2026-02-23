import sys
import uuid

from tools._registry import register

DEFINITION = {
    "type": "function",
    "function": {
        "name": "store_memory",
        "description": (
            "Store or update user memories based on relevant messages. "
            "Call this when the user mentions persistent parking-relevant info "
            "such as their city, parking permits, vehicle type, work schedule, etc."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "relevant_messages": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "The user message texts containing memory-worthy information.",
                },
            },
            "required": ["relevant_messages"],
        },
    },
}

register(DEFINITION, sys.modules[__name__], agent_name="memory_manager")


async def run(*, relevant_messages: list[str], session_id: uuid.UUID | None = None, call_id: str | None = None, **kwargs) -> dict:
    from agent.subagents.memory_manager import run_agent

    return await run_agent(relevant_messages=relevant_messages, session_id=session_id)
