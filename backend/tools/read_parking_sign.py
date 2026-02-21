import sys

from tools._registry import register
from tools.context import ToolContext

DEFINITION = {
    "type": "function",
    "function": {
        "name": "read_parking_sign",
        "description": "Extract text and rules from a parking sign image.",
        "parameters": {
            "type": "object",
            "properties": {},
        },
    },
}

register(DEFINITION, sys.modules[__name__])


async def run(context: ToolContext | None = None, **kwargs) -> dict:
    """Delegate to the parking sign reader sub-agent."""
    from agent.subagents.parking_sign_reader import run_agent

    if context is None:
        return {"error": "No context provided to read_parking_sign"}

    return await run_agent(
        entries=context.entries,
        uploaded_file_id=context.uploaded_file_id,
    )
