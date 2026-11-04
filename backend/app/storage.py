import uuid
from pathlib import Path

from app.config import settings


def upload_dir() -> Path:
    path = Path(settings.upload_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def save_file(data: bytes, extension: str) -> str:
    """Save bytes under a random name and return that name."""
    stored_name = f"{uuid.uuid4().hex}{extension}"
    (upload_dir() / stored_name).write_bytes(data)
    return stored_name


def file_path(stored_name: str) -> Path:
    return upload_dir() / stored_name
