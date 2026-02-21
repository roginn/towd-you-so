import uuid
from dataclasses import dataclass, field

from db.models import EntryModel


@dataclass
class ToolContext:
    session_id: uuid.UUID
    entries: list[EntryModel] = field(default_factory=list)
    uploaded_file_id: uuid.UUID | None = None
