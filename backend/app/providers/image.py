from __future__ import annotations

import asyncio
import base64
import struct
import zlib
from pathlib import Path
from typing import Protocol
from urllib.parse import quote

from app.config import Settings
from app.schemas.domain import OutfitCandidate, StyleTaskRequest
from app.schemas.quality import ImageCandidate


class TryOnImageProvider(Protocol):
    async def generate_candidates(
        self,
        *,
        task_id: str,
        request: StyleTaskRequest,
        outfit: OutfitCandidate,
        prompt: str,
        attempt: int,
        count: int,
    ) -> list[ImageCandidate]:
        ...


class LocalTryOnImageProvider:
    """Deterministic image provider that mimics multi-candidate generation."""

    async def generate_candidates(
        self,
        *,
        task_id: str,
        request: StyleTaskRequest,
        outfit: OutfitCandidate,
        prompt: str,
        attempt: int,
        count: int,
    ) -> list[ImageCandidate]:
        candidates: list[ImageCandidate] = []
        for index in range(count):
            # Later candidates and retries become slightly better. This makes QC/retry behavior testable.
            quality_boost = min(0.08, attempt * 0.035 + index * 0.02)
            candidates.append(
                ImageCandidate(
                    candidate_id=f"{task_id}_tryon_{attempt}_{index}",
                    image_url=self._preview_tryon(task_id, attempt, index),
                    prompt=prompt,
                    provider="local",
                    attempt=attempt,
                    metadata={
                        "identity_score": min(0.95, 0.82 + quality_boost),
                        "garment_score": min(0.93, 0.78 + quality_boost),
                        "artifact_score": min(0.96, 0.86 + quality_boost),
                        "realism_score": min(0.94, 0.8 + quality_boost),
                    },
                )
            )
        return candidates

    def _preview_tryon(self, task_id: str, attempt: int, index: int) -> str:
        accent_sets = [
            ((232, 93, 79), (76, 111, 145), (48, 57, 64)),
            ((184, 79, 119), (91, 120, 103), (63, 60, 72)),
            ((47, 118, 104), (108, 98, 88), (187, 132, 47)),
        ]
        top, bottom, shoe = accent_sets[(attempt + index) % len(accent_sets)]
        png = _preview_tryon_png(top=top, bottom=bottom, shoe=shoe)
        encoded = base64.b64encode(png).decode("ascii")
        return f"data:image/png;base64,{encoded}"

        svg = f"""
        <svg xmlns="http://www.w3.org/2000/svg" width="720" height="1080" viewBox="0 0 720 1080">
          <rect width="720" height="1080" fill="#f5f4f0"/>
          <rect x="110" y="70" width="500" height="940" rx="42" fill="#fffdf9"/>
          <circle cx="360" cy="178" r="58" fill="#b98773"/>
          <path d="M268 266 C298 232 422 232 452 266 L500 526 L220 526 Z" fill="#e85d4f"/>
          <path d="M250 526 L342 526 L328 868 L232 868 Z" fill="#4c6f91"/>
          <path d="M378 526 L470 526 L488 868 L392 868 Z" fill="#4c6f91"/>
          <rect x="212" y="870" width="132" height="34" rx="17" fill="#303940"/>
          <rect x="376" y="870" width="132" height="34" rx="17" fill="#303940"/>
          <text x="360" y="970" text-anchor="middle" font-family="Arial" font-size="28" font-weight="700" fill="#1e2428">QC Try-on Candidate</text>
          <text x="360" y="1010" text-anchor="middle" font-family="Arial" font-size="20" fill="#687078">{task_id} · attempt {attempt + 1} · image {index + 1}</text>
        </svg>
        """
        return f"data:image/svg+xml;charset=utf-8,{quote(svg)}"


class ArkSeedreamImageProvider:
    """Ark/Seedream try-on generation provider.

    The provider generates multiple independent candidates so the graph can keep only
    images that pass identity, garment, artifact, and realism quality gates.
    """

    def __init__(self, settings: Settings) -> None:
        if not settings.ark_api_key:
            raise RuntimeError("STYLE_BACKEND_ARK_API_KEY is required for Ark image generation")
        try:
            from openai import OpenAI
        except Exception as exc:  # pragma: no cover - optional production dependency
            raise RuntimeError("openai is required for Ark image generation") from exc
        self.settings = settings
        self.client = OpenAI(api_key=settings.ark_api_key, base_url=settings.ark_base_url)

    async def generate_candidates(
        self,
        *,
        task_id: str,
        request: StyleTaskRequest,
        outfit: OutfitCandidate,
        prompt: str,
        attempt: int,
        count: int,
    ) -> list[ImageCandidate]:
        references = self._reference_images(request, outfit)
        concurrency = max(1, min(count, self.settings.image_generation_concurrency))
        semaphore = asyncio.Semaphore(concurrency)

        async def generate_one(index: int) -> ImageCandidate:
            async with semaphore:
                response = await asyncio.to_thread(
                    self.client.images.generate,
                    model=self.settings.ark_image_model,
                    prompt=self._prompt(prompt, attempt=attempt, index=index),
                    size=self.settings.ark_image_size,  # type: ignore[arg-type]
                    response_format="url",  # type: ignore[arg-type]
                    extra_body={
                        "image": references,
                        "watermark": self.settings.ark_watermark,
                    },
                )
                image_url = response.data[0].url if response.data else None
                if not image_url:
                    raise RuntimeError("Ark Seedream did not return an image URL")
                return ImageCandidate(
                    candidate_id=f"{task_id}_ark_{attempt}_{index}",
                    image_url=image_url,
                    prompt=prompt,
                    provider="ark-seedream",
                    attempt=attempt,
                    metadata={},
                )

        return list(await asyncio.gather(*(generate_one(index) for index in range(count))))

    def _reference_images(self, request: StyleTaskRequest, outfit: OutfitCandidate) -> list[str]:
        local_path = self.settings.storage_dir / request.photo_object_key
        person_reference = _file_to_data_url(local_path) if local_path.exists() else request.photo_url
        product_references = [item.image_url for item in outfit.items if item.image_url]
        return [person_reference, *product_references][:15]

    def _prompt(self, prompt: str, *, attempt: int, index: int) -> str:
        correction = ""
        if attempt > 0:
            correction = "\nThis is a retry. Improve identity fidelity, garment fidelity, complete full-body framing, and realism."
        return f"{prompt}\n\nCandidate {index + 1}.{correction}"


def _file_to_data_url(path: Path) -> str:
    mime = {
        ".png": "image/png",
        ".webp": "image/webp",
        ".gif": "image/gif",
    }.get(path.suffix.lower(), "image/jpeg")
    data = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{data}"


def _preview_tryon_png(
    *,
    top: tuple[int, int, int],
    bottom: tuple[int, int, int],
    shoe: tuple[int, int, int],
) -> bytes:
    width = 360
    height = 540
    pixels = bytearray(width * height * 3)
    _fill_rect(pixels, width, 0, 0, width, height, (245, 244, 240))
    _fill_rect(pixels, width, 55, 35, 305, 505, (255, 253, 249))
    _fill_circle(pixels, width, 180, 88, 29, (185, 135, 115))
    _fill_polygon(pixels, width, [(134, 133), (226, 133), (250, 263), (110, 263)], top)
    _fill_polygon(pixels, width, [(125, 263), (171, 263), (164, 434), (116, 434)], bottom)
    _fill_polygon(pixels, width, [(189, 263), (235, 263), (244, 434), (196, 434)], bottom)
    _fill_rect(pixels, width, 106, 435, 172, 452, shoe)
    _fill_rect(pixels, width, 188, 435, 254, 452, shoe)
    return _encode_png(width, height, bytes(pixels))


def _fill_rect(
    pixels: bytearray,
    width: int,
    left: int,
    top: int,
    right: int,
    bottom: int,
    color: tuple[int, int, int],
) -> None:
    height = len(pixels) // (width * 3)
    for y in range(max(0, top), min(height, bottom)):
        row = y * width * 3
        for x in range(max(0, left), min(width, right)):
            offset = row + x * 3
            pixels[offset : offset + 3] = bytes(color)


def _fill_circle(
    pixels: bytearray,
    width: int,
    cx: int,
    cy: int,
    radius: int,
    color: tuple[int, int, int],
) -> None:
    height = len(pixels) // (width * 3)
    radius_squared = radius * radius
    for y in range(max(0, cy - radius), min(height, cy + radius + 1)):
        row = y * width * 3
        for x in range(max(0, cx - radius), min(width, cx + radius + 1)):
            if (x - cx) * (x - cx) + (y - cy) * (y - cy) <= radius_squared:
                offset = row + x * 3
                pixels[offset : offset + 3] = bytes(color)


def _fill_polygon(
    pixels: bytearray,
    width: int,
    points: list[tuple[int, int]],
    color: tuple[int, int, int],
) -> None:
    height = len(pixels) // (width * 3)
    min_y = max(0, min(y for _, y in points))
    max_y = min(height - 1, max(y for _, y in points))
    for y in range(min_y, max_y + 1):
        intersections: list[float] = []
        for index, (x1, y1) in enumerate(points):
            x2, y2 = points[(index + 1) % len(points)]
            if (y1 <= y < y2) or (y2 <= y < y1):
                intersections.append(x1 + (y - y1) * (x2 - x1) / (y2 - y1))
        intersections.sort()
        for left, right in zip(intersections[0::2], intersections[1::2]):
            _fill_rect(pixels, width, int(left), y, int(right) + 1, y + 1, color)


def _encode_png(width: int, height: int, rgb: bytes) -> bytes:
    stride = width * 3
    scanlines = b"".join(b"\x00" + rgb[y * stride : (y + 1) * stride] for y in range(height))
    return b"".join(
        [
            b"\x89PNG\r\n\x1a\n",
            _png_chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)),
            _png_chunk(b"IDAT", zlib.compress(scanlines, level=9)),
            _png_chunk(b"IEND", b""),
        ]
    )


def _png_chunk(chunk_type: bytes, data: bytes) -> bytes:
    checksum = zlib.crc32(chunk_type + data) & 0xFFFFFFFF
    return struct.pack(">I", len(data)) + chunk_type + data + struct.pack(">I", checksum)
