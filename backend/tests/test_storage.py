from __future__ import annotations

from io import BytesIO

from PIL import Image

from app.config import Settings
from app.providers.storage import LocalObjectStorage


def _large_jpeg() -> bytes:
    image = Image.effect_noise((3000, 3000), 100).convert("RGB")
    buffer = BytesIO()
    image.save(buffer, format="JPEG", quality=98)
    return buffer.getvalue()


def test_local_storage_downsizes_oversized_model_images(tmp_path):
    settings = Settings(
        storage_dir=tmp_path,
        upload_dir=tmp_path / "uploads",
        generated_dir=tmp_path / "generated",
    )
    storage = LocalObjectStorage(settings)
    original = _large_jpeg()
    assert len(original) > 10 * 1024 * 1024

    object_key, _ = storage.save_file(BytesIO(original), "person.jpg", "image/jpeg")

    saved = (tmp_path / object_key).read_bytes()
    assert len(saved) <= 7 * 1024 * 1024
