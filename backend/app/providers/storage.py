from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import BinaryIO, Protocol
from uuid import uuid4

from PIL import Image, ImageOps, UnidentifiedImageError

from app.config import Settings

MAX_MODEL_IMAGE_BYTES = 7 * 1024 * 1024
MAX_MODEL_IMAGE_DIMENSION = 2048
JPEG_QUALITIES = (88, 82, 76, 70, 64)


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
        payload, suffix = _prepare_image_upload(stream.read(), suffix, content_type)
        object_key = f"uploads/{uuid4().hex}{suffix}"
        target = self.settings.storage_dir / object_key
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
        public_key = object_key.replace("\\", "/")
        public_url = f"{self.settings.public_base_url}/objects/{public_key}"
        return object_key, public_url


def _prepare_image_upload(payload: bytes, suffix: str, content_type: str | None) -> tuple[bytes, str]:
    if not content_type or not content_type.startswith("image/"):
        return payload, suffix

    try:
        image = Image.open(BytesIO(payload))
        image = ImageOps.exif_transpose(image)
    except (OSError, UnidentifiedImageError):
        return payload, suffix

    needs_resize = max(image.size) > MAX_MODEL_IMAGE_DIMENSION
    needs_reencode = needs_resize or len(payload) > MAX_MODEL_IMAGE_BYTES
    if not needs_reencode:
        return payload, suffix

    if needs_resize:
        image.thumbnail((MAX_MODEL_IMAGE_DIMENSION, MAX_MODEL_IMAGE_DIMENSION), Image.Resampling.LANCZOS)
    image = _jpeg_compatible(image)

    best_payload = payload
    for quality in JPEG_QUALITIES:
        compressed = _encode_jpeg(image, quality)
        if len(compressed) < len(best_payload):
            best_payload = compressed
        if len(compressed) <= MAX_MODEL_IMAGE_BYTES:
            return compressed, ".jpg"
    return best_payload, ".jpg"


def _jpeg_compatible(image: Image.Image) -> Image.Image:
    if image.mode == "RGB":
        return image
    if image.mode in {"RGBA", "LA"} or (image.mode == "P" and "transparency" in image.info):
        background = Image.new("RGB", image.size, "white")
        background.paste(image.convert("RGBA"), mask=image.convert("RGBA").split()[-1])
        return background
    return image.convert("RGB")


def _encode_jpeg(image: Image.Image, quality: int) -> bytes:
    output = BytesIO()
    image.save(output, format="JPEG", quality=quality, optimize=True, progressive=True)
    return output.getvalue()
