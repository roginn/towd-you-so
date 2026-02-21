import sys
import uuid
import base64

import httpx

from tools._registry import register
from config import settings
from db.database import get_db
from db.repository import get_uploaded_file
from storage.backend import LocalFileStorageBackend

DEFINITION = {
    "type": "function",
    "function": {
        "name": "ocr_parking_sign",
        "description": (
            "Send a parking sign image to the OCR pipeline. "
            "Returns an array of strings, one per detected sign part."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "file_id": {
                    "type": "string",
                    "description": "The uploaded file UUID of the parking sign image.",
                },
            },
            "required": ["file_id"],
        },
    },
}

register(DEFINITION, sys.modules[__name__])


async def run(*, file_id: str, **kwargs) -> dict:
    """Read image from DB/disk, send to Roboflow workflow, return OCR results."""
    file_uuid = uuid.UUID(file_id)

    # 1. Look up the uploaded file record
    async with get_db() as db:
        uploaded = await get_uploaded_file(db, file_uuid)
        if not uploaded:
            return {"error": f"File not found: {file_id}"}
        storage_key = uploaded.storage_key
        mime_type = uploaded.mime_type

    # 2. Read image bytes from disk
    storage = LocalFileStorageBackend()
    import aiofiles

    path = storage.upload_dir / storage_key
    async with aiofiles.open(path, "rb") as f:
        image_bytes = await f.read()
    image_b64 = base64.b64encode(image_bytes).decode("ascii")

    # 3. Call Roboflow workflow API
    payload = {
        "api_key": settings.ROBOFLOW_API_KEY,
        "inputs": {
            "image": {
                "type": "base64",
                "value": image_b64,
            }
        },
    }

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(settings.ROBOFLOW_WORKFLOW_URL, json=payload)
        resp.raise_for_status()
        result = resp.json()

    # 4. Extract sign text strings from workflow output
    # The workflow returns {"outputs": [{"signs": ["text1", "text2", ...]}]}
    outputs = result.get("outputs", [{}])
    signs = outputs[0].get("signs", []) if outputs else []
    return {"signs": signs}
