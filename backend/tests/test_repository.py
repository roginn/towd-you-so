import uuid

import pytest

from db.models import EntryKind, EntryStatus, SessionModel
from db.repository import (
    append_entry,
    create_session,
    get_entry,
    get_session,
    get_session_entries,
    mark_entry_status,
)


@pytest.mark.asyncio
async def test_create_session(db_session):
    session = await create_session(db_session)
    assert isinstance(session, SessionModel)
    assert session.id is not None


@pytest.mark.asyncio
async def test_create_session_with_parent(db_session):
    parent = await create_session(db_session)
    child = await create_session(db_session, parent_id=parent.id)
    assert child.parent_id == parent.id


@pytest.mark.asyncio
async def test_get_session_nonexistent(db_session):
    result = await get_session(db_session, uuid.uuid4())
    assert result is None


@pytest.mark.asyncio
async def test_get_session_existing(db_session):
    session = await create_session(db_session)
    fetched = await get_session(db_session, session.id)
    assert fetched is not None
    assert fetched.id == session.id


@pytest.mark.asyncio
async def test_append_entry_non_executable_status_is_none(db_session, test_session_id):
    entry = await append_entry(
        db_session, test_session_id, EntryKind.USER_MESSAGE, {"content": "hello"}
    )
    assert entry.status is None


@pytest.mark.asyncio
async def test_append_entry_tool_call_status_is_pending(db_session, test_session_id):
    entry = await append_entry(
        db_session,
        test_session_id,
        EntryKind.TOOL_CALL,
        {"call_id": "c1", "tool_name": "vision", "arguments": {}},
    )
    assert entry.status == EntryStatus.PENDING


@pytest.mark.asyncio
async def test_get_session_entries_ordered(db_session, test_session_id):
    await append_entry(
        db_session, test_session_id, EntryKind.USER_MESSAGE, {"content": "first"}
    )
    await append_entry(
        db_session, test_session_id, EntryKind.ASSISTANT_MESSAGE, {"content": "second"}
    )
    entries = await get_session_entries(db_session, test_session_id)
    assert len(entries) == 2
    assert entries[0].data["content"] == "first"
    assert entries[1].data["content"] == "second"


@pytest.mark.asyncio
async def test_mark_entry_status(db_session, test_session_id):
    entry = await append_entry(
        db_session,
        test_session_id,
        EntryKind.TOOL_CALL,
        {"call_id": "c1", "tool_name": "t", "arguments": {}},
    )
    assert entry.status == EntryStatus.PENDING
    await mark_entry_status(db_session, entry.id, EntryStatus.DONE)
    updated = await get_entry(db_session, entry.id)
    assert updated.status == EntryStatus.DONE


@pytest.mark.asyncio
async def test_get_entry(db_session, test_session_id):
    entry = await append_entry(
        db_session, test_session_id, EntryKind.USER_MESSAGE, {"content": "hi"}
    )
    fetched = await get_entry(db_session, entry.id)
    assert fetched is not None
    assert fetched.id == entry.id
    assert fetched.kind == EntryKind.USER_MESSAGE
