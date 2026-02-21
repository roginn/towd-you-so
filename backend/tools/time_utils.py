import sys
from datetime import datetime, timezone

from tools._registry import register

DEFINITION = {
    "type": "function",
    "function": {
        "name": "get_current_time",
        "description": "Get the current date, time, and day of week.",
        "parameters": {"type": "object", "properties": {}},
    },
}

register(DEFINITION, sys.modules[__name__])


async def run(**kwargs) -> dict:
    """Return the current date and time in UTC."""
    now = datetime.now(timezone.utc)
    return {
        "datetime": now.isoformat(),
        "day_of_week": now.strftime("%A"),
    }
