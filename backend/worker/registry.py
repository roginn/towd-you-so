import asyncio
import uuid
from dataclasses import dataclass, field

from fastapi import WebSocket


class ToolBatch:
    """Tracks which tool calls are still outstanding for one LLM response."""

    def __init__(self, call_ids: list[str]):
        self.pending: set[str] = set(call_ids)

    def mark_done(self, call_id: str) -> bool:
        """Mark a call as complete. Returns True when the last one finishes."""
        self.pending.discard(call_id)
        return len(self.pending) == 0


@dataclass
class SessionSlot:
    queue: asyncio.Queue = field(default_factory=asyncio.Queue)
    websocket: WebSocket | None = None
    batch: ToolBatch | None = None


_slots: dict[uuid.UUID, SessionSlot] = {}


def get_or_create_slot(session_id: uuid.UUID) -> SessionSlot:
    if session_id not in _slots:
        _slots[session_id] = SessionSlot()
    return _slots[session_id]


def set_websocket(session_id: uuid.UUID, ws: WebSocket | None) -> None:
    slot = get_or_create_slot(session_id)
    slot.websocket = ws


def enqueue_entry(session_id: uuid.UUID, entry_id: uuid.UUID) -> None:
    slot = get_or_create_slot(session_id)
    slot.queue.put_nowait(entry_id)


async def push_to_client(session_id: uuid.UUID, data: dict) -> None:
    slot = _slots.get(session_id)
    if slot and slot.websocket:
        await slot.websocket.send_json(data)


def register_batch(session_id: uuid.UUID, call_ids: list[str]) -> None:
    """Create a new ToolBatch for the given session."""
    slot = get_or_create_slot(session_id)
    slot.batch = ToolBatch(call_ids)


def mark_batch_done(session_id: uuid.UUID, call_id: str) -> bool:
    """Record one tool result. Returns True when the batch is complete."""
    slot = _slots.get(session_id)
    if slot and slot.batch:
        done = slot.batch.mark_done(call_id)
        if done:
            slot.batch = None
        return done
    return False


def remove_slot(session_id: uuid.UUID) -> None:
    _slots.pop(session_id, None)
