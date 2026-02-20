import asyncio
import uuid
from dataclasses import dataclass, field

from fastapi import WebSocket


@dataclass
class SessionSlot:
    queue: asyncio.Queue = field(default_factory=asyncio.Queue)
    websocket: WebSocket | None = None


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


def remove_slot(session_id: uuid.UUID) -> None:
    _slots.pop(session_id, None)
