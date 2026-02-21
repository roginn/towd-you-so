import uuid
from datetime import datetime, timezone
from types import SimpleNamespace

from db.models import EntryKind, EntryStatus
from interface.models import entry_to_wire


def _make_entry(
    kind=EntryKind.USER_MESSAGE,
    data=None,
    status=None,
):
    return SimpleNamespace(
        id=uuid.uuid4(),
        session_id=uuid.uuid4(),
        kind=kind,
        data=data or {"content": "hello"},
        status=status,
        created_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
    )


def test_entry_to_wire_structure():
    entry = _make_entry()
    wire = entry_to_wire(entry)
    assert wire["type"] == "entry"
    assert "entry" in wire
    inner = wire["entry"]
    assert inner["id"] == str(entry.id)
    assert inner["session_id"] == str(entry.session_id)
    assert inner["kind"] == "user_message"
    assert inner["data"] == {"content": "hello"}
    assert inner["created_at"] == "2025-01-01T00:00:00+00:00"


def test_entry_to_wire_nullable_status():
    entry = _make_entry(status=None)
    wire = entry_to_wire(entry)
    assert wire["entry"]["status"] is None


def test_entry_to_wire_with_status():
    entry = _make_entry(kind=EntryKind.TOOL_CALL, status=EntryStatus.PENDING)
    wire = entry_to_wire(entry)
    assert wire["entry"]["status"] == "pending"
