import sys
import uuid

from tools._registry import register

DEFINITION = {
    "type": "function",
    "function": {
        "name": "task_location",
        "description": (
            "Delegate a location-related task to the location sub-agent. "
            "Use this to save a parking sign's location or search for nearby saved signs. "
            "Provide a natural language task description."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "task_description": {
                    "type": "string",
                    "description": (
                        "Natural language instruction, e.g. "
                        "'Save this parking sign at: 20th st between illinois and georgia, San Francisco' "
                        "or 'Search for parking signs near 20th and texas st, San Francisco'."
                    ),
                },
                "uploaded_file_id": {
                    "type": "string",
                    "description": "UUID of the uploaded parking sign image (for save tasks).",
                },
                "sign_text": {
                    "type": "string",
                    "description": "The OCR-extracted sign text/rules (for save tasks).",
                },
            },
            "required": ["task_description"],
        },
    },
}

register(DEFINITION, sys.modules[__name__], agent_name="location_agent")


async def run(
    *,
    task_description: str,
    uploaded_file_id: str | None = None,
    sign_text: str | None = None,
    session_id: uuid.UUID | None = None,
    call_id: str | None = None,
    **kwargs,
) -> dict:
    from agent.subagents.location_agent import run_agent

    return await run_agent(
        task_description=task_description,
        session_id=session_id,
        uploaded_file_id=uploaded_file_id,
        sign_text=sign_text,
    )
