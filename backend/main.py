import asyncio
import logging
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, UploadFile, WebSocket, WebSocketDisconnect
from fastapi import HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles


from agent.orchestrator import start_session
from worker.worker import run_worker
from worker.registry import (
    get_or_create_slot,
    remove_slot,
    set_websocket,
)
from config import settings
from db.database import get_db
from db.repository import (
    create_session,
    create_uploaded_file,
    get_session,
    get_session_entries,
    get_uploaded_file_by_storage_key,
)
from interface.models import (
    CreateSessionResponse,
    InboundWSMessage,
    UploadResponse,
    entry_to_wire,
)
from storage.backend import LocalFileStorageBackend

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
storage = LocalFileStorageBackend()


@asynccontextmanager
async def lifespan(app: FastAPI):
    Path(settings.UPLOAD_DIR).mkdir(parents=True, exist_ok=True)
    logger.info("Uploads dir ready (run 'alembic upgrade head' to apply migrations)")
    yield


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")


# --- REST endpoints ---


@app.post("/api/sessions", response_model=CreateSessionResponse)
async def create_session_endpoint():
    async with get_db() as db:
        session = await create_session(db)
    return CreateSessionResponse(session_id=str(session.id))


@app.post("/api/upload", response_model=UploadResponse)
async def upload_file(file: UploadFile):
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {file.content_type}. Allowed: {ALLOWED_IMAGE_TYPES}",
        )

    data = await file.read()
    storage_key = await storage.save(data, file.filename or "upload.bin")
    url = storage.url_for(storage_key)

    async with get_db() as db:
        await create_uploaded_file(
            db,
            storage_key=storage_key,
            original_filename=file.filename or "upload.bin",
            mime_type=file.content_type or "application/octet-stream",
            size_bytes=len(data),
        )

    return UploadResponse(file_id=storage_key, url=url)


@app.get("/api/sessions/{session_id}/entries")
async def get_entries(session_id: uuid.UUID):
    async with get_db() as db:
        session = await get_session(db, session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        entries = await get_session_entries(db, session_id)
    return [entry_to_wire(e)["entry"] for e in entries]


# --- Settings ---


class DateTimeOverrideRequest(BaseModel):
    datetime: str | None = None


@app.post("/api/settings/datetime-override")
async def set_datetime_override(body: DateTimeOverrideRequest):
    from datetime import datetime as dt, timezone
    from tools.time_utils import set_override, clear_override

    if body.datetime is None:
        clear_override()
        return {"ok": True, "datetime": None}

    try:
        parsed = dt.fromisoformat(body.datetime).replace(tzinfo=timezone.utc)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid datetime format")

    set_override(parsed)
    return {"ok": True, "datetime": parsed.isoformat()}


# --- WebSocket ---


@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: uuid.UUID):
    async with get_db() as db:
        session = await get_session(db, session_id)
        if not session:
            await websocket.close(code=4004, reason="Session not found")
            return

    await websocket.accept()

    slot = get_or_create_slot(session_id)
    set_websocket(session_id, websocket)
    worker_task = asyncio.create_task(run_worker(session_id, slot.queue))

    try:
        while True:
            raw = await websocket.receive_json()
            msg = InboundWSMessage(**raw)

            uploaded_file_id = None
            image_url = None
            if msg.file_id:
                image_url = storage.url_for(msg.file_id)
                async with get_db() as db:
                    uploaded_file = await get_uploaded_file_by_storage_key(db, msg.file_id)
                    if uploaded_file:
                        uploaded_file_id = uploaded_file.id

            await start_session(session_id, msg.content, uploaded_file_id, image_url)
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected for session %s", session_id)
    finally:
        worker_task.cancel()
        set_websocket(session_id, None)
        remove_slot(session_id)
