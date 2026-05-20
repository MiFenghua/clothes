from __future__ import annotations

from typing import BinaryIO
from uuid import uuid4
from pathlib import Path

from app.providers.storage import ObjectStorage


class S3ObjectStorage(ObjectStorage):
    """S3-compatible object storage for AWS S3, Cloudflare R2, Ali OSS gateways, etc."""

    def __init__(self, *, bucket: str, public_base_url: str, prefix: str = "style") -> None:
        try:
            import boto3
        except Exception as exc:  # pragma: no cover - optional production dependency
            raise RuntimeError("boto3 is required for S3ObjectStorage") from exc
        self.client = boto3.client("s3")
        self.bucket = bucket
        self.public_base_url = public_base_url.rstrip("/")
        self.prefix = prefix.strip("/")

    def save_file(self, stream: BinaryIO, filename: str, content_type: str | None = None) -> tuple[str, str]:
        suffix = Path(filename).suffix.lower() or ".jpg"
        key = f"{self.prefix}/uploads/{uuid4().hex}{suffix}"
        extra_args = {"ContentType": content_type} if content_type else None
        if extra_args:
            self.client.upload_fileobj(stream, self.bucket, key, ExtraArgs=extra_args)
        else:
            self.client.upload_fileobj(stream, self.bucket, key)
        return key, f"{self.public_base_url}/{key}"

