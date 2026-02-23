import sys
import uuid

from tools._registry import register

DEFINITION = {
    "type": "function",
    "function": {
        "name": "save_parking_sign_location",
        "description": (
            "Save a parking sign's geocoded location to the database."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "uploaded_file_id": {
                    "type": "string",
                    "description": "UUID of the uploaded parking sign image.",
                },
                "latitude": {
                    "type": "number",
                    "description": "Latitude of the sign location.",
                },
                "longitude": {
                    "type": "number",
                    "description": "Longitude of the sign location.",
                },
                "description": {
                    "type": "string",
                    "description": "Original user description of the location.",
                },
                "sign_text": {
                    "type": "string",
                    "description": "OCR-extracted text/rules from the parking sign.",
                },
            },
            "required": ["uploaded_file_id", "latitude", "longitude", "description", "sign_text"],
        },
    },
}

register(DEFINITION, sys.modules[__name__])


async def run(
    *,
    uploaded_file_id: str,
    latitude: float,
    longitude: float,
    description: str,
    sign_text: str,
    **kwargs,
) -> dict:
    from db.database import get_db
    from db.repository import create_parking_sign_location

    async with get_db() as db:
        location = await create_parking_sign_location(
            db,
            uploaded_file_id=uuid.UUID(uploaded_file_id),
            latitude=latitude,
            longitude=longitude,
            description=description,
            sign_text=sign_text,
        )

    return {
        "id": str(location.id),
        "latitude": location.latitude,
        "longitude": location.longitude,
        "description": location.description,
    }
