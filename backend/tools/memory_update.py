import sys
import uuid

from tools._registry import register

DEFINITION = {
    "type": "function",
    "function": {
        "name": "memory_update",
        "description": "Update the content of an existing user memory.",
        "parameters": {
            "type": "object",
            "properties": {
                "memory_id": {
                    "type": "string",
                    "description": "The UUID of the memory to update.",
                },
                "content": {
                    "type": "string",
                    "description": "The new memory text.",
                },
            },
            "required": ["memory_id", "content"],
        },
    },
}

register(DEFINITION, sys.modules[__name__])


async def run(*, memory_id: str, content: str, **kwargs) -> dict:
    from db.database import get_db
    from db.repository import update_memory

    async with get_db() as db:
        memory = await update_memory(db, uuid.UUID(memory_id), content)

    if memory is None:
        return {"error": f"Memory {memory_id} not found"}

    return {"id": str(memory.id), "content": memory.content}
