import io
import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from main import app


@pytest.mark.asyncio
async def test_create_session():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/sessions")
    assert resp.status_code == 200
    data = resp.json()
    assert "session_id" in data
    # Validate it's a valid UUID
    uuid.UUID(data["session_id"])


@pytest.mark.asyncio
async def test_upload_valid_image():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/upload",
            files={"file": ("photo.jpg", b"fake image bytes", "image/jpeg")},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert "file_id" in data
    assert "url" in data
    assert data["file_id"].endswith(".jpg")


@pytest.mark.asyncio
async def test_upload_invalid_type():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/upload",
            files={"file": ("doc.pdf", b"pdf bytes", "application/pdf")},
        )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_get_entries_empty():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Create a session first
        resp = await client.post("/api/sessions")
        session_id = resp.json()["session_id"]

        resp = await client.get(f"/api/sessions/{session_id}/entries")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_get_entries_nonexistent_session():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get(f"/api/sessions/{uuid.uuid4()}/entries")
    assert resp.status_code == 404
