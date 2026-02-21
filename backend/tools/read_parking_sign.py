import sys
import uuid

from tools._registry import register

DEFINITION = {
    "type": "function",
    "function": {
        "name": "read_parking_sign",
        "description": "Extract text and rules from a parking sign image.",
        "parameters": {
            "type": "object",
            "properties": {
                "file_id": {
                    "type": "string",
                    "description": "The uploaded file ID of the parking sign image.",
                },
            },
            "required": ["file_id"],
        },
    },
}

register(DEFINITION, sys.modules[__name__])


async def run(*, file_id: str, **kwargs) -> dict:
    """Delegate to the parking sign reader sub-agent."""
    from agent.subagents.parking_sign_reader import run_agent

    return await run_agent(uploaded_file_id=uuid.UUID(file_id))
