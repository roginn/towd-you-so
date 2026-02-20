from pydantic import BaseModel

from db.models import EntryModel


class CreateSessionResponse(BaseModel):
    session_id: str


class UploadResponse(BaseModel):
    file_id: str
    url: str


class InboundWSMessage(BaseModel):
    content: str
    file_id: str | None = None


def entry_to_wire(entry: EntryModel) -> dict:
    """Serialize an EntryModel to a dict suitable for WebSocket transmission."""
    return {
        "type": "entry",
        "entry": {
            "id": str(entry.id),
            "session_id": str(entry.session_id),
            "kind": entry.kind.value,
            "data": entry.data,
            "status": entry.status.value if entry.status else None,
            "created_at": entry.created_at.isoformat(),
        },
    }
