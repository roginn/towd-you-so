import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import (
    EXECUTABLE_KINDS,
    EntryKind,
    EntryModel,
    EntryStatus,
    SessionModel,
)


async def create_session(
    db: AsyncSession, parent_id: uuid.UUID | None = None
) -> SessionModel:
    session = SessionModel(parent_id=parent_id)
    db.add(session)
    await db.flush()
    return session


async def get_session(db: AsyncSession, session_id: uuid.UUID) -> SessionModel | None:
    return await db.get(SessionModel, session_id)


async def append_entry(
    db: AsyncSession,
    session_id: uuid.UUID,
    kind: EntryKind,
    data: dict,
) -> EntryModel:
    status = EntryStatus.PENDING if kind in EXECUTABLE_KINDS else None
    entry = EntryModel(session_id=session_id, kind=kind, data=data, status=status)
    db.add(entry)
    await db.flush()
    return entry


async def mark_entry_status(
    db: AsyncSession, entry_id: uuid.UUID, status: EntryStatus
) -> None:
    entry = await db.get(EntryModel, entry_id)
    if entry:
        entry.status = status
        await db.flush()


async def get_session_entries(
    db: AsyncSession, session_id: uuid.UUID
) -> list[EntryModel]:
    result = await db.execute(
        select(EntryModel)
        .where(EntryModel.session_id == session_id)
        .order_by(EntryModel.created_at)
    )
    return list(result.scalars().all())


async def get_entry(db: AsyncSession, entry_id: uuid.UUID) -> EntryModel | None:
    return await db.get(EntryModel, entry_id)
