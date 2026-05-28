from __future__ import annotations

import unittest

from app.agents.graph import StyleAgentGraph
from app.config import Settings
from app.providers.image import LocalTryOnImageProvider
from app.providers.query_planner import ProductSearchPlan
from app.providers.search import ProductSearchProvider
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


def request(**overrides) -> StyleTaskRequest:
    base = {
        "photo_url": "https://example.com/person.jpg",
        "photo_object_key": "uploads/person.jpg",
        "budget": Budget(min=300, max=900),
        "preferences": StylePreferences(liked_style="干净,显比例", avoid=None, height_cm=165, usual_size="M"),
        "marketplaces": [Marketplace.taobao, Marketplace.tmall],
    }
    base.update(overrides)
    return StyleTaskRequest(**base)


class ModelPhotoProfileProvider:
    async def analyze(self, *, task_id, request):
        return StyleProfile(
            body_proportion="balanced",
            undertone="neutral",
            hair_tone="dark",
            style_signals=["模型风格"],
            fit_advice=["模型版型"],
            palette=["model-white"],
            photo_quality=PhotoQuality(
                is_full_body=True,
                face_visible=True,
                lighting="good",
                occlusion="low",
                resolution_score=0.9,
            ),
            confidence=0.9,
            summary="模型画像。",
        )


class ModelQueryPlanner:
    source = "model_test"

    def __init__(self, plans: list[ProductSearchPlan]) -> None:
        self.plans = plans

    async def build_queries(self, *, request, profile, constraints):
        return self.plans


class RecordingSearchProvider(ProductSearchProvider):
    source_id = "recording"

    def __init__(self) -> None:
        self.calls: list[dict] = []

    async def search(
        self,
        *,
        query,
        category,
        colors,
        style_tags,
        fit_tags,
        marketplaces,
        budget,
        limit,
    ):
        self.calls.append(
            {
                "query": query,
                "category": category,
                "colors": colors,
                "style_tags": style_tags,
                "fit_tags": fit_tags,
            }
        )
        return [
            ProductCandidate(
                product_id=f"{category.value}_from_model",
                marketplace=Marketplace.taobao,
                source_provider=self.source_id,
                category=category,
                title=f"{query} raw marketplace title",
                price=199,
                price_text="¥199",
                image_url="https://img.alicdn.com/model-item.jpg",
                product_url="https://s.click.taobao.com/model-item",
                sizes=["S", "M", "L"],
                colors=colors,
                style_tags=style_tags,
                fit_tags=fit_tags,
                source_reliability=0.95,
                score=0.93,
            )
        ]


class ModelOutfitPlanner:
    source = "model_outfit_test"

    def __init__(self, product_ids: list[str]) -> None:
        self.product_ids = product_ids

    async def build_outfits(self, *, request, profile, constraints, products):
        from app.providers.outfit_planner import ModelOutfitCandidatePlan, ModelOutfitItemPlan

        return [
            ModelOutfitCandidatePlan(
                title="模型指定非固定组合",
                items=[
                    ModelOutfitItemPlan(
                        product_id=product_id,
                        selection_reason="模型选择该商品。",
                        match_reason="模型认为适合用户。",
                        selection_scores={"model": 0.91},
                    )
                    for product_id in self.product_ids
                ],
                score=0.91,
                score_breakdown={"model_fit": 0.91, "product_quality": 0.93},
                why_this_works=["模型解释一。", "模型解释二。"],
            )
        ]


class ModelDecisionChainTests(unittest.IsolatedAsyncioTestCase):
    async def test_graph_fails_when_model_query_planner_is_missing(self) -> None:
        graph = StyleAgentGraph(
            settings=Settings(),
            tracer=InMemoryTraceRecorder(),
            search_provider=RecordingSearchProvider(),
            image_provider=LocalTryOnImageProvider(),
            photo_provider=ModelPhotoProfileProvider(),
            outfit_planner=ModelOutfitPlanner(["top_from_model"]),
        )

        with self.assertRaisesRegex(RuntimeError, "模型检索计划不可用"):
            await graph.run(task_id="task_no_query_model", request=request())

    async def test_search_uses_model_category_and_metadata_without_keyword_rules(self) -> None:
        search_provider = RecordingSearchProvider()
        graph = StyleAgentGraph(
            settings=Settings(),
            tracer=InMemoryTraceRecorder(),
            search_provider=search_provider,
            image_provider=LocalTryOnImageProvider(),
            photo_provider=ModelPhotoProfileProvider(),
            query_planner=ModelQueryPlanner(
                [
                    ProductSearchPlan(
                        query="模型原始关键词 珍珠白 显比例",
                        category=ProductCategory.shoes,
                        colors=["model-silver"],
                        style_tags=["model-style"],
                        fit_tags=["model-fit"],
                    )
                ]
            ),
            outfit_planner=ModelOutfitPlanner(["shoes_from_model"]),
        )

        result = await graph.run(task_id="task_model_search_metadata", request=request())

        self.assertEqual(result.status, TaskStatus.succeeded)
        self.assertEqual(search_provider.calls[0]["query"], "模型原始关键词 珍珠白 显比例")
        self.assertEqual(search_provider.calls[0]["category"], ProductCategory.shoes)
        self.assertEqual(result.outfit.items[0].category, ProductCategory.shoes)
        self.assertEqual(result.outfit.items[0].colors, ["model-silver"])
        self.assertEqual(result.outfit.items[0].style_tags, ["model-style"])

    async def test_model_outfit_planner_controls_composition_without_fixed_paths(self) -> None:
        search_provider = RecordingSearchProvider()
        graph = StyleAgentGraph(
            settings=Settings(),
            tracer=InMemoryTraceRecorder(),
            search_provider=search_provider,
            image_provider=LocalTryOnImageProvider(),
            photo_provider=ModelPhotoProfileProvider(),
            query_planner=ModelQueryPlanner(
                [
                    ProductSearchPlan(query="模型包袋", category=ProductCategory.bag),
                    ProductSearchPlan(query="模型鞋履", category=ProductCategory.shoes),
                ]
            ),
            outfit_planner=ModelOutfitPlanner(["bag_from_model", "shoes_from_model"]),
        )

        result = await graph.run(task_id="task_model_composition", request=request(scene=Scene.daily))

        self.assertEqual(result.status, TaskStatus.succeeded)
        self.assertEqual([item.product_id for item in result.outfit.items], ["bag_from_model", "shoes_from_model"])
        self.assertEqual({item.category for item in result.outfit.items}, {ProductCategory.bag, ProductCategory.shoes})


if __name__ == "__main__":
    unittest.main()
