import sys
import uuid

from tools._registry import register

DEFINITION = {
    "type": "function",
    "function": {
        "name": "memory_delete",
        "description": "Delete an existing user memory.",
        "parameters": {
            "type": "object",
            "properties": {
                "memory_id": {
                    "type": "string",
                    "description": "The UUID of the memory to delete.",
                },
            },
            "required": ["memory_id"],
        },
    },
}

register(DEFINITION, sys.modules[__name__])


async def run(*, memory_id: str, **kwargs) -> dict:
    from db.database import get_db
    from db.repository import delete_memory

    async with get_db() as db:
        deleted = await delete_memory(db, uuid.UUID(memory_id))

    if not deleted:
        return {"error": f"Memory {memory_id} not found"}

    return {"deleted": memory_id}
