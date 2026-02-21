import uuid

import pytest
import pytest_asyncio
from sqlalchemy import JSON, String, event
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.ext.compiler import compiles

from db.models import Base, SessionModel

# ---------------------------------------------------------------------------
# SQLite compatibility shims for PostgreSQL-specific column types
# ---------------------------------------------------------------------------

@compiles(JSONB, "sqlite")
def _compile_jsonb_sqlite(type_, compiler, **kw):
    return compiler.visit_JSON(JSON(), **kw)


# UUID(as_uuid=True) → CHAR(36) on SQLite
@compiles(UUID, "sqlite")
def _compile_uuid_sqlite(type_, compiler, **kw):
    return "CHAR(36)"


# ---------------------------------------------------------------------------
# Async SQLite engine + session fixtures
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def db_engine():
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine):
    factory = async_sessionmaker(db_engine, expire_on_commit=False)
    async with factory() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def test_session_id(db_session: AsyncSession) -> uuid.UUID:
    """Create a SessionModel row and return its id."""
    s = SessionModel()
    db_session.add(s)
    await db_session.flush()
    return s.id


@pytest_asyncio.fixture(autouse=True)
async def override_get_db(db_session: AsyncSession, monkeypatch):
    """Monkeypatch db.database.get_db so all production code uses the test session."""
    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def _fake_get_db():
        yield db_session

    import db.database
    import main
    import agent.orchestrator
    import conductor.conductor

    # Patch get_db on every module that imports it directly
    monkeypatch.setattr(db.database, "get_db", _fake_get_db)
    monkeypatch.setattr(main, "get_db", _fake_get_db)
    monkeypatch.setattr(agent.orchestrator, "get_db", _fake_get_db)
    monkeypatch.setattr(conductor.conductor, "get_db", _fake_get_db)

