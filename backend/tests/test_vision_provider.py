from __future__ import annotations

import asyncio
import unittest

from app.config import Settings
from app.providers.vision import ArkImageQualityScoringProvider
from app.schemas.domain import Budget, StyleTaskRequest
from app.schemas.quality import ImageCandidate


class ArkImageQualityScoringProviderTests(unittest.IsolatedAsyncioTestCase):
    async def test_image_quality_candidates_are_scored_concurrently(self) -> None:
        fake_vision = _SlowVisionClient()
        provider = object.__new__(ArkImageQualityScoringProvider)
        provider.settings = Settings(ark_api_key="test-key", image_quality_concurrency=3)
        provider.vision = fake_vision

        scores = await provider.score_candidates(
            task_id="task_qc",
            request=StyleTaskRequest(
                photo_url="http://127.0.0.1:8000/objects/uploads/person.jpg",
                photo_object_key="uploads/person.jpg",
                budget=Budget(min=300, max=800),
            ),
            candidates=[
                ImageCandidate(
                    candidate_id=f"candidate_{index}",
                    image_url=f"https://example.com/{index}.jpg",
                    prompt="prompt",
                    provider="ark-seedream",
                    attempt=0,
                )
                for index in range(3)
            ],
            product_image_urls=["https://example.com/top.jpg"],
        )

        self.assertEqual({"candidate_0", "candidate_1", "candidate_2"}, set(scores))
        self.assertGreater(fake_vision.max_active, 1)


class _SlowVisionClient:
    def __init__(self) -> None:
        self.active = 0
        self.max_active = 0

    def local_or_remote_image(self, request: StyleTaskRequest) -> str:
        return request.photo_url

    async def create_json(self, *, prompt: str, image_urls: list[str]) -> dict:
        self.active += 1
        self.max_active = max(self.max_active, self.active)
        try:
            await asyncio.sleep(0.08)
            return {
                "identity_score": 0.9,
                "garment_score": 0.9,
                "artifact_score": 0.9,
                "realism_score": 0.9,
            }
        finally:
            self.active -= 1


if __name__ == "__main__":
    unittest.main()
