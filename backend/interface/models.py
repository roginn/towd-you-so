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
            "kind": entry.kind.value if hasattr(entry.kind, "value") else entry.kind,
            "data": entry.data,
            "status": entry.status.value if hasattr(entry.status, "value") else entry.status,
            "created_at": entry.created_at.isoformat(),
        },
    }
