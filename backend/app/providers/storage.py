from __future__ import annotations

import shutil
from pathlib import Path
from typing import BinaryIO, Protocol
from uuid import uuid4

from app.config import Settings


class ObjectStorage(Protocol):
    def save_file(self, stream: BinaryIO, filename: str, content_type: str | None = None) -> tuple[str, str]:
        ...


class LocalObjectStorage:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.settings.upload_dir.mkdir(parents=True, exist_ok=True)
        self.settings.generated_dir.mkdir(parents=True, exist_ok=True)

    def save_file(self, stream: BinaryIO, filename: str, content_type: str | None = None) -> tuple[str, str]:
        suffix = Path(filename).suffix.lower() or ".jpg"
        object_key = f"uploads/{uuid4().hex}{suffix}"
        target = self.settings.storage_dir / object_key
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("wb") as output:
            shutil.copyfileobj(stream, output)
        public_key = object_key.replace("\\", "/")
        public_url = f"{self.settings.public_base_url}/objects/{public_key}"
        return object_key, public_url
