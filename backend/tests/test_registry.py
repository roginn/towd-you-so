import asyncio
import uuid

import pytest

from worker.registry import (
    SessionSlot,
    ToolBatch,
    _slots,
    enqueue_entry,
    get_or_create_slot,
    mark_batch_done,
    push_to_client,
    register_batch,
    remove_slot,
    set_websocket,
)


@pytest.fixture(autouse=True)
def clear_slots():
    _slots.clear()
    yield
    _slots.clear()


def test_get_or_create_slot_creates_new():
    sid = uuid.uuid4()
    slot = get_or_create_slot(sid)
    assert isinstance(slot, SessionSlot)
    assert slot.websocket is None


def test_get_or_create_slot_returns_same():
    sid = uuid.uuid4()
    slot1 = get_or_create_slot(sid)
    slot2 = get_or_create_slot(sid)
    assert slot1 is slot2


def test_set_websocket():
    sid = uuid.uuid4()
    sentinel = object()
    set_websocket(sid, sentinel)
    assert get_or_create_slot(sid).websocket is sentinel
    set_websocket(sid, None)
    assert get_or_create_slot(sid).websocket is None


def test_enqueue_entry():
    sid = uuid.uuid4()
    eid = uuid.uuid4()
    enqueue_entry(sid, eid)
    slot = get_or_create_slot(sid)
    assert slot.queue.get_nowait() == eid


@pytest.mark.asyncio
async def test_push_to_client_no_websocket():
    sid = uuid.uuid4()
    # Should not raise even if no slot exists
    await push_to_client(sid, {"test": True})


def test_remove_slot():
    sid = uuid.uuid4()
    get_or_create_slot(sid)
    assert sid in _slots
    remove_slot(sid)
    assert sid not in _slots


# --- ToolBatch tests ---


def test_tool_batch_single():
    batch = ToolBatch(["c1"])
    assert batch.mark_done("c1") is True


def test_tool_batch_multiple():
    batch = ToolBatch(["c1", "c2", "c3"])
    assert batch.mark_done("c1") is False
    assert batch.mark_done("c2") is False
    assert batch.mark_done("c3") is True


def test_tool_batch_pending_tracks_ids():
    batch = ToolBatch(["c1", "c2"])
    assert batch.pending == {"c1", "c2"}
    batch.mark_done("c1")
    assert batch.pending == {"c2"}


def test_register_and_mark_batch_done():
    sid = uuid.uuid4()
    register_batch(sid, ["c1", "c2"])
    assert mark_batch_done(sid, "c1") is False
    assert mark_batch_done(sid, "c2") is True
    # Batch should be cleared after completion
    slot = get_or_create_slot(sid)
    assert slot.batch is None


def test_mark_batch_done_no_batch():
    sid = uuid.uuid4()
    get_or_create_slot(sid)
    # No batch registered — should return False
    assert mark_batch_done(sid, "c1") is False


def test_mark_batch_done_no_slot():
    sid = uuid.uuid4()
    # No slot at all — should return False
    assert mark_batch_done(sid, "c1") is False
