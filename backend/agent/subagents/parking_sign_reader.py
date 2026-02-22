import uuid

from tools.ocr_parking_sign import run as ocr_run

PARKING_SIGN_READER_TOOLS = [
    "ocr_parking_sign",
]


async def run_agent(
    uploaded_file_id: uuid.UUID | None = None,
) -> dict:
    """Run the parking sign OCR tool and return the extracted text."""
    if uploaded_file_id is None:
        return {"text": "No file ID provided."}

    result = await ocr_run(file_id=str(uploaded_file_id))

    if "error" in result:
        return {"text": f"Error reading sign: {result['error']}"}

    signs = result.get("signs", [])
    if not signs:
        return {"text": "No text detected on the parking sign."}

    return {"text": "\n\n".join(signs)}
