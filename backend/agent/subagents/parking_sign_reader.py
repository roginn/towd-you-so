import uuid

from db.database import get_db
from db.models import EntryKind
from db.repository import append_entry
from interface.models import entry_to_wire
from tools.ocr_parking_sign import run as ocr_run
from worker.registry import push_to_client

PARKING_SIGN_READER_TOOLS = [
    "ocr_parking_sign",
]


async def run_agent(
    uploaded_file_id: uuid.UUID | None = None,
    session_id: uuid.UUID | None = None,
) -> dict:
    """Run the parking sign OCR tool and return the extracted text."""
    if uploaded_file_id is None:
        return {"text": "No file ID provided."}

    call_id = f"psr_{uuid.uuid4().hex[:12]}"
    arguments = {"file_id": str(uploaded_file_id)}

    # Write TOOL_CALL entry
    if session_id:
        tool_call_data = {
            "call_id": call_id,
            "tool_name": "ocr_parking_sign",
            "arguments": arguments,
            "agent_name": "parking_sign_reader",
        }
        async with get_db() as db:
            tc_entry = await append_entry(db, session_id, EntryKind.TOOL_CALL, tool_call_data)
        await push_to_client(session_id, entry_to_wire(tc_entry))

    result = await ocr_run(file_id=str(uploaded_file_id))

    # Write TOOL_RESULT entry
    if session_id:
        tool_result_data = {"call_id": call_id, "result": result}
        async with get_db() as db:
            tr_entry = await append_entry(db, session_id, EntryKind.TOOL_RESULT, tool_result_data)
        await push_to_client(session_id, entry_to_wire(tr_entry))

    if "error" in result:
        return {"text": f"Error reading sign: {result['error']}"}

    signs = result.get("signs", [])
    if not signs:
        return {"text": "No text detected on the parking sign."}

    return {"text": "\n\n".join(signs)}
