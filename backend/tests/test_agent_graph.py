from __future__ import annotations

import unittest

from app.agents.graph import StyleAgentGraph
from app.config import Settings
from app.providers.image import LocalTryOnImageProvider, TryOnImageProvider
from app.providers.search import LocalDemoSearchProvider
from app.providers.tracing import InMemoryTraceRecorder
from app.schemas.domain import (
    Budget,
    Marketplace,
    PhotoQuality,
    ProductCandidate,
    ProductCategory,
    Scene,
    StylePreferences,
    StyleProfile,
    StyleTaskRequest,
    TaskStatus,
)
from app.schemas.quality import ImageCandidate


def request(**overrides) -> StyleTaskRequest:
    base = {
        "photo_url": "https://example.com/person.jpg",
        "photo_object_key": "uploads/person.jpg",
        "budget": Budget(min=300, max=900),
        "preferences": StylePreferences(liked_style="干净,显比例", avoid=None, height_cm=165, usual_size="M"),
        "marketplaces": [Marketplace.taobao, Marketplace.tmall, Marketplace.amazon],
    }
    base.update(overrides)
    return StyleTaskRequest(**base)


class LowQualityImageProvider(TryOnImageProvider):
    async def generate_candidates(self, *, task_id, request, outfit, prompt, attempt, count):
        return [
            ImageCandidate(
                candidate_id=f"{task_id}_bad_{attempt}_{index}",
                image_url=f"https://generated.example.com/{task_id}/bad-{attempt}-{index}.png",
                prompt=prompt,
                provider="low-quality",
                attempt=attempt,
                metadata={
                    "identity_score": 0.7,
                    "garment_score": 0.72,
                    "artifact_score": 0.81,
                    "realism_score": 0.76,
                },
            )
            for index in range(count)
        ]


class AvoidConflictSearchProvider(LocalDemoSearchProvider):
    async def search(self, *, query, marketplaces, budget, limit):
        products = await super().search(query=query, marketplaces=marketplaces, budget=budget, limit=limit)
        return [product.model_copy(update={"title": f"{product.title} 荧光色"}) for product in products]


class EmptySearchProvider(LocalDemoSearchProvider):
    async def search(self, *, query, marketplaces, budget, limit):
        return []


class MissingBagSearchProvider(LocalDemoSearchProvider):
    async def search(self, *, query, marketplaces, budget, limit):
        products = await super().search(query=query, marketplaces=marketplaces, budget=budget, limit=limit)
        if products and products[0].category == ProductCategory.bag:
            return []
        return products


class BadPhotoProfileProvider:
    async def analyze(self, *, task_id, request):
        return StyleProfile(
            body_proportion="balanced",
            undertone="neutral",
            hair_tone="dark",
            style_signals=["干净"],
            fit_advice=["高腰线"],
            palette=["ivory", "black"],
            photo_quality=PhotoQuality(
                is_full_body=False,
                face_visible=False,
                lighting="poor",
                occlusion="high",
                resolution_score=0.3,
            ),
            confidence=0.4,
            summary="照片质量不足。",
        )


class AgentGraphTests(unittest.IsolatedAsyncioTestCase):
    async def test_graph_returns_success_when_recommendation_and_image_pass(self) -> None:
        tracer = InMemoryTraceRecorder()
        graph = StyleAgentGraph(
            settings=Settings(),
            tracer=tracer,
            search_provider=LocalDemoSearchProvider(),
            image_provider=LocalTryOnImageProvider(),
        )

        result = await graph.run(task_id="task_success", request=request())

        self.assertEqual(result.status, TaskStatus.succeeded)
        self.assertIsNotNone(result.outfit)
        self.assertIsNotNone(result.try_on_image_url)
        self.assertGreaterEqual(result.recommendation_report.final_score, 0.82)
        self.assertGreaterEqual(result.image_quality_report.overall_score, 0.84)
        self.assertGreater(len(tracer.by_task("task_success")), 5)

    async def test_avoid_term_rejects_hard_selling_bad_outfit(self) -> None:
        tracer = InMemoryTraceRecorder()
        graph = StyleAgentGraph(
            settings=Settings(),
            tracer=tracer,
            search_provider=AvoidConflictSearchProvider(),
            image_provider=LocalTryOnImageProvider(),
        )

        result = await graph.run(
            task_id="task_avoid",
            request=request(preferences=StylePreferences(liked_style="干净", avoid="荧光色")),
        )

        self.assertEqual(result.status, TaskStatus.failed)
        self.assertIn("宁缺毋滥", result.user_message)
        self.assertIsNone(result.try_on_image_url)

    async def test_low_quality_images_return_partial_result_without_tryon_image(self) -> None:
        tracer = InMemoryTraceRecorder()
        graph = StyleAgentGraph(
            settings=Settings(),
            tracer=tracer,
            search_provider=LocalDemoSearchProvider(),
            image_provider=LowQualityImageProvider(),
        )

        result = await graph.run(task_id="task_partial", request=request())

        self.assertEqual(result.status, TaskStatus.partial_succeeded)
        self.assertIsNotNone(result.outfit)
        self.assertIsNone(result.try_on_image_url)
        self.assertIsNotNone(result.image_quality_report)
        self.assertFalse(result.image_quality_report.accepted)

    async def test_bad_photo_quality_blocks_before_product_search(self) -> None:
        tracer = InMemoryTraceRecorder()
        graph = StyleAgentGraph(
            settings=Settings(),
            tracer=tracer,
            search_provider=LocalDemoSearchProvider(),
            image_provider=LocalTryOnImageProvider(),
            photo_provider=BadPhotoProfileProvider(),
        )

        result = await graph.run(task_id="task_bad_photo", request=request())

        self.assertEqual(result.status, TaskStatus.failed)
        self.assertIn("照片质量不足", result.user_message)
        self.assertIsNone(result.outfit)

    async def test_empty_product_data_fails_recommendation_gate(self) -> None:
        tracer = InMemoryTraceRecorder()
        graph = StyleAgentGraph(
            settings=Settings(),
            tracer=tracer,
            search_provider=EmptySearchProvider(),
            image_provider=LocalTryOnImageProvider(),
        )

        result = await graph.run(task_id="task_empty_products", request=request())

        self.assertEqual(result.status, TaskStatus.failed)
        self.assertIn("没有足够可信的商品", result.user_message)
        self.assertIsNone(result.try_on_image_url)

    async def test_missing_optional_bag_still_builds_core_outfit(self) -> None:
        tracer = InMemoryTraceRecorder()
        graph = StyleAgentGraph(
            settings=Settings(),
            tracer=tracer,
            search_provider=MissingBagSearchProvider(),
            image_provider=LocalTryOnImageProvider(),
        )

        result = await graph.run(task_id="task_missing_bag", request=request())

        self.assertEqual(result.status, TaskStatus.succeeded)
        self.assertIsNotNone(result.outfit)
        categories = {item.category for item in result.outfit.items}
        self.assertIn(ProductCategory.top, categories)
        self.assertIn(ProductCategory.bottom, categories)
        self.assertNotIn(ProductCategory.bag, categories)

    async def test_retry_image_reuses_approved_outfit_without_recommendation_search(self) -> None:
        tracer = InMemoryTraceRecorder()
        graph = StyleAgentGraph(
            settings=Settings(),
            tracer=tracer,
            search_provider=LocalDemoSearchProvider(),
            image_provider=LowQualityImageProvider(),
        )
        partial = await graph.run(task_id="task_retry_source", request=request())
        self.assertEqual(partial.status, TaskStatus.partial_succeeded)
        self.assertIsNotNone(partial.outfit)

        retry_graph = StyleAgentGraph(
            settings=Settings(),
            tracer=tracer,
            search_provider=EmptySearchProvider(),
            image_provider=LocalTryOnImageProvider(),
        )
        retried = await retry_graph.retry_image(
            task_id="task_retry_source",
            request=request(),
            outfit=partial.outfit,
            recommendation_report=partial.recommendation_report,
            rejected_outfits=partial.alternatives_rejected,
        )

        self.assertEqual(retried.status, TaskStatus.succeeded)
        self.assertIsNotNone(retried.try_on_image_url)

    async def test_wardrobe_items_are_added_to_product_pool(self) -> None:
        tracer = InMemoryTraceRecorder()
        owned_outerwear = ProductCandidate(
            product_id="wardrobe_coat_1",
            marketplace=Marketplace.owned,
            category=ProductCategory.outerwear,
            title="米色西装外套",
            price=0,
            price_text="衣橱已有",
            image_url="https://example.com/owned-coat.png",
            product_url="owned://wardrobe/wardrobe_coat_1",
            colors=["ivory"],
            style_tags=["通勤", "干净"],
            fit_tags=["利落"],
            source_reliability=0.94,
            score=0.99,
        )
        graph = StyleAgentGraph(
            settings=Settings(),
            tracer=tracer,
            search_provider=LocalDemoSearchProvider(),
            image_provider=LocalTryOnImageProvider(),
            wardrobe_products=lambda ids: [owned_outerwear] if "wardrobe_coat_1" in ids else [],
        )

        result = await graph.run(
            task_id="task_wardrobe",
            request=request(scene=Scene.commute, wardrobe_item_ids=["wardrobe_coat_1"]),
        )

        self.assertEqual(result.status, TaskStatus.succeeded)
        self.assertIsNotNone(result.outfit)
        self.assertTrue(any(item.product_id == "wardrobe_coat_1" for item in result.outfit.items))


if __name__ == "__main__":
    unittest.main()
