import sys

from tools._registry import register

DEFINITION = {
    "type": "function",
    "function": {
        "name": "memory_list",
        "description": "List all existing user memories with their IDs.",
        "parameters": {"type": "object", "properties": {}},
    },
}

register(DEFINITION, sys.modules[__name__])


async def run(**kwargs) -> dict:
    from db.database import get_db
    from db.repository import list_memories

    async with get_db() as db:
        memories = await list_memories(db)

    return {
        "memories": [
            {"id": str(m.id), "content": m.content}
            for m in memories
        ]
    }
