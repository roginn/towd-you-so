import uuid
from abc import ABC, abstractmethod
from pathlib import Path

import aiofiles

from config import settings


class StorageBackend(ABC):
    @abstractmethod
    async def save(self, data: bytes, filename: str) -> str:
        """Save bytes and return a file_id."""

    @abstractmethod
    def url_for(self, file_id: str) -> str:
        """Return a public URL for the given file_id."""


class LocalFileStorageBackend(StorageBackend):
    def __init__(self, upload_dir: str = settings.UPLOAD_DIR):
        self.upload_dir = Path(upload_dir)
        self.upload_dir.mkdir(parents=True, exist_ok=True)

    async def save(self, data: bytes, filename: str) -> str:
        ext = Path(filename).suffix or ".bin"
        file_id = f"{uuid.uuid4()}{ext}"
        path = self.upload_dir / file_id
        async with aiofiles.open(path, "wb") as f:
            await f.write(data)
        return file_id

    def url_for(self, file_id: str) -> str:
        return f"{settings.BASE_URL}/uploads/{file_id}"
