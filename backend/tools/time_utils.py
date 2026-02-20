from datetime import datetime, timezone


async def run(**kwargs) -> dict:
    """Return the current date and time in UTC."""
    now = datetime.now(timezone.utc)
    return {
        "datetime": now.isoformat(),
        "day_of_week": now.strftime("%A"),
    }
