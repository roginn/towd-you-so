import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import (
    EXECUTABLE_KINDS,
    EntryKind,
    EntryModel,
    EntryStatus,
    MemoryModel,
    ParkingSignLocationModel,
    SessionModel,
    UploadedFileModel,
)


async def create_session(
    db: AsyncSession, parent_id: uuid.UUID | None = None
) -> SessionModel:
    session = SessionModel(parent_id=parent_id)
    db.add(session)
    await db.flush()
    return session


async def list_sessions(db: AsyncSession) -> list[SessionModel]:
    result = await db.execute(
        select(SessionModel).order_by(SessionModel.started_at.desc())
    )
    return list(result.scalars().all())


async def get_session(db: AsyncSession, session_id: uuid.UUID) -> SessionModel | None:
    return await db.get(SessionModel, session_id)


async def append_entry(
    db: AsyncSession,
    session_id: uuid.UUID,
    kind: EntryKind,
    data: dict,
    uploaded_file_id: uuid.UUID | None = None,
) -> EntryModel:
    status = EntryStatus.PENDING if kind in EXECUTABLE_KINDS else None
    entry = EntryModel(
        session_id=session_id,
        kind=kind,
        data=data,
        status=status,
        uploaded_file_id=uploaded_file_id,
    )
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


async def create_uploaded_file(
    db: AsyncSession,
    storage_key: str,
    original_filename: str,
    mime_type: str,
    size_bytes: int,
) -> UploadedFileModel:
    uploaded_file = UploadedFileModel(
        storage_key=storage_key,
        original_filename=original_filename,
        mime_type=mime_type,
        size_bytes=size_bytes,
    )
    db.add(uploaded_file)
    await db.flush()
    return uploaded_file


async def get_uploaded_file(
    db: AsyncSession, file_id: uuid.UUID
) -> UploadedFileModel | None:
    return await db.get(UploadedFileModel, file_id)


async def get_uploaded_file_by_storage_key(
    db: AsyncSession, storage_key: str
) -> UploadedFileModel | None:
    result = await db.execute(
        select(UploadedFileModel).where(UploadedFileModel.storage_key == storage_key)
    )
    return result.scalar_one_or_none()


# --- Memories ---


async def create_memory(db: AsyncSession, content: str) -> MemoryModel:
    memory = MemoryModel(content=content)
    db.add(memory)
    await db.flush()
    return memory


async def update_memory(
    db: AsyncSession, memory_id: uuid.UUID, content: str
) -> MemoryModel | None:
    memory = await db.get(MemoryModel, memory_id)
    if memory:
        memory.content = content
        await db.flush()
    return memory


async def delete_memory(db: AsyncSession, memory_id: uuid.UUID) -> bool:
    memory = await db.get(MemoryModel, memory_id)
    if memory:
        await db.delete(memory)
        await db.flush()
        return True
    return False


async def list_memories(db: AsyncSession) -> list[MemoryModel]:
    result = await db.execute(
        select(MemoryModel).order_by(MemoryModel.created_at)
    )
    return list(result.scalars().all())


# --- Parking Sign Locations ---


async def create_parking_sign_location(
    db: AsyncSession,
    uploaded_file_id: uuid.UUID,
    latitude: float,
    longitude: float,
    description: str,
    sign_text: str,
) -> ParkingSignLocationModel:
    location = ParkingSignLocationModel(
        uploaded_file_id=uploaded_file_id,
        latitude=latitude,
        longitude=longitude,
        description=description,
        sign_text=sign_text,
    )
    db.add(location)
    await db.flush()
    return location


async def list_parking_sign_locations(
    db: AsyncSession,
) -> list[ParkingSignLocationModel]:
    result = await db.execute(
        select(ParkingSignLocationModel).order_by(
            ParkingSignLocationModel.created_at
        )
    )
    return list(result.scalars().all())


async def get_parking_sign_location(
    db: AsyncSession, location_id: uuid.UUID
) -> ParkingSignLocationModel | None:
    return await db.get(ParkingSignLocationModel, location_id)
