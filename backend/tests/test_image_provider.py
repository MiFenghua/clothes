from __future__ import annotations

import base64
import threading
import time
import unittest
from types import SimpleNamespace

from app.config import Settings
from app.providers.image import ArkSeedreamImageProvider, LocalTryOnImageProvider
from app.schemas.domain import Budget, Marketplace, OutfitCandidate, OutfitItem, ProductCategory, StyleTaskRequest


def _style_request() -> StyleTaskRequest:
    return StyleTaskRequest(
        photo_url="http://127.0.0.1:8000/objects/uploads/person.jpg",
        photo_object_key="uploads/person.jpg",
        budget=Budget(min=300, max=800),
    )


def _outfit() -> OutfitCandidate:
    return OutfitCandidate(
        candidate_id="outfit_1",
        title="Preview outfit",
        items=[
            OutfitItem(
                product_id="top_1",
                marketplace=Marketplace.taobao,
                category=ProductCategory.top,
                title="Top",
                price=199,
                image_url="https://example.com/top.jpg",
                product_url="https://example.com/top",
                selection_reason="Top layer",
                match_reason="Matches",
            )
        ],
        total_price=199,
        score=0.9,
        score_breakdown={},
        why_this_works=["Preview"],
    )


class LocalTryOnImageProviderTests(unittest.IsolatedAsyncioTestCase):
    async def test_local_tryon_provider_returns_raster_data_url_for_android_preview(self) -> None:
        provider = LocalTryOnImageProvider()

        candidates = await provider.generate_candidates(
            task_id="task_preview",
            request=_style_request(),
            outfit=_outfit(),
            prompt="preview",
            attempt=0,
            count=1,
        )

        image_url = candidates[0].image_url
        self.assertTrue(image_url.startswith("data:image/png;base64,"))
        payload = base64.b64decode(image_url.split(",", 1)[1])
        self.assertTrue(payload.startswith(b"\x89PNG\r\n\x1a\n"))


class ArkSeedreamImageProviderTests(unittest.IsolatedAsyncioTestCase):
    async def test_ark_tryon_candidates_are_generated_concurrently(self) -> None:
        fake_images = _BlockingImagesApi()
        provider = object.__new__(ArkSeedreamImageProvider)
        provider.settings = Settings(ark_api_key="test-key", image_generation_concurrency=3)
        provider.client = SimpleNamespace(images=fake_images)

        candidates = await provider.generate_candidates(
            task_id="task_fast",
            request=_style_request(),
            outfit=_outfit(),
            prompt="preview",
            attempt=0,
            count=3,
        )

        self.assertEqual(3, len(candidates))
        self.assertGreater(fake_images.max_active, 1)


class _BlockingImagesApi:
    def __init__(self) -> None:
        self.active = 0
        self.max_active = 0
        self.lock = threading.Lock()
        self.calls = 0

    def generate(self, **_kwargs):
        with self.lock:
            self.active += 1
            self.calls += 1
            call_number = self.calls
            self.max_active = max(self.max_active, self.active)
        try:
            time.sleep(0.08)
            return SimpleNamespace(data=[SimpleNamespace(url=f"https://example.com/generated-{call_number}.jpg")])
        finally:
            with self.lock:
                self.active -= 1


if __name__ == "__main__":
    unittest.main()
