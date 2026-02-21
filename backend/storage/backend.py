import base64
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

# Later: AWS S3 or Cloudflare R2
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

    async def read_as_data_url(self, storage_key: str, mime_type: str) -> str:
        path = self.upload_dir / storage_key
        async with aiofiles.open(path, "rb") as f:
            data = await f.read()
        encoded = base64.b64encode(data).decode("ascii")
        return f"data:{mime_type};base64,{encoded}"
