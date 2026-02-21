import sys

from tools._registry import register

DEFINITION = {
    "type": "function",
    "function": {
        "name": "read_parking_sign",
        "description": "Extract text and rules from a parking sign image.",
        "parameters": {
            "type": "object",
            "properties": {
                "image_url": {
                    "type": "string",
                    "description": "URL of the parking sign image",
                }
            },
            "required": ["image_url"],
        },
    },
}

register(DEFINITION, sys.modules[__name__])


async def run(**kwargs) -> dict:
    """Delegate to the parking sign reader sub-agent."""
    from agent.subagents.parking_sign_reader import run_agent

    return await run_agent(**kwargs)
