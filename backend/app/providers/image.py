from __future__ import annotations

import asyncio
import base64
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
        candidates: list[ImageCandidate] = []
        for index in range(count):
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
            candidates.append(
                ImageCandidate(
                    candidate_id=f"{task_id}_ark_{attempt}_{index}",
                    image_url=image_url,
                    prompt=prompt,
                    provider="ark-seedream",
                    attempt=attempt,
                    metadata={},
                )
            )
        return candidates

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
