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

_override_dt: datetime | None = None


def set_override(dt: datetime) -> None:
    global _override_dt
    _override_dt = dt


def get_override() -> datetime | None:
    return _override_dt


def clear_override() -> None:
    global _override_dt
    _override_dt = None


async def run(**kwargs) -> dict:
    """Return the current date and time in UTC (or the override if set)."""
    now = _override_dt if _override_dt is not None else datetime.now(timezone.utc)
    return {
        "datetime": now.isoformat(),
        "day_of_week": now.strftime("%A"),
    }
