from __future__ import annotations

import base64
import unittest

from app.providers.image import LocalTryOnImageProvider
from app.schemas.domain import Budget, Marketplace, OutfitCandidate, OutfitItem, ProductCategory, StyleTaskRequest


class LocalTryOnImageProviderTests(unittest.IsolatedAsyncioTestCase):
    async def test_local_tryon_provider_returns_raster_data_url_for_android_preview(self) -> None:
        provider = LocalTryOnImageProvider()

        candidates = await provider.generate_candidates(
            task_id="task_preview",
            request=StyleTaskRequest(
                photo_url="http://127.0.0.1:8000/objects/uploads/person.jpg",
                photo_object_key="uploads/person.jpg",
                budget=Budget(min=300, max=800),
            ),
            outfit=OutfitCandidate(
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
            ),
            prompt="preview",
            attempt=0,
            count=1,
        )

        image_url = candidates[0].image_url
        self.assertTrue(image_url.startswith("data:image/png;base64,"))
        payload = base64.b64decode(image_url.split(",", 1)[1])
        self.assertTrue(payload.startswith(b"\x89PNG\r\n\x1a\n"))


if __name__ == "__main__":
    unittest.main()
