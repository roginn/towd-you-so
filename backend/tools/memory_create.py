import sys

from tools._registry import register

DEFINITION = {
    "type": "function",
    "function": {
        "name": "memory_create",
        "description": "Create a new user memory.",
        "parameters": {
            "type": "object",
            "properties": {
                "content": {
                    "type": "string",
                    "description": "Human-readable memory text, e.g. 'User lives in San Francisco'.",
                },
            },
            "required": ["content"],
        },
    },
}

register(DEFINITION, sys.modules[__name__])


async def run(*, content: str, **kwargs) -> dict:
    from db.database import get_db
    from db.repository import create_memory

    async with get_db() as db:
        memory = await create_memory(db, content)

    return {"id": str(memory.id), "content": memory.content}
