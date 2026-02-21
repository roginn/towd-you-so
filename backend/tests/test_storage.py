import pytest

from storage.backend import LocalFileStorageBackend


@pytest.mark.asyncio
async def test_save_returns_file_id_with_extension(tmp_path):
    backend = LocalFileStorageBackend(upload_dir=str(tmp_path))
    file_id = await backend.save(b"fake image data", "photo.jpg")
    assert file_id.endswith(".jpg")
    assert (tmp_path / file_id).exists()


@pytest.mark.asyncio
async def test_save_no_extension_defaults_to_bin(tmp_path):
    backend = LocalFileStorageBackend(upload_dir=str(tmp_path))
    file_id = await backend.save(b"data", "noext")
    assert file_id.endswith(".bin")


@pytest.mark.asyncio
async def test_url_for(tmp_path):
    backend = LocalFileStorageBackend(upload_dir=str(tmp_path))
    url = backend.url_for("abc123.jpg")
    assert url.endswith("/uploads/abc123.jpg")
