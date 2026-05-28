from __future__ import annotations

import unittest

from app.agents.graph import StyleAgentGraph
from app.config import Settings
from app.providers.image import LocalTryOnImageProvider, TryOnImageProvider
from app.providers.outfit_planner import ModelOutfitCandidatePlan, ModelOutfitItemPlan
from app.providers.query_planner import ProductSearchPlan
from app.providers.tracing import InMemoryTraceRecorder
from app.schemas.domain import (
    Budget,
    Marketplace,
    OutfitCandidate,
    OutfitItem,
    PhotoQuality,
    PreferenceConstraints,
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
        "preferences": StylePreferences(liked_style="clean, proportion", avoid=None, height_cm=165, usual_size="M"),
        "marketplaces": [Marketplace.taobao, Marketplace.tmall],
    }
    base.update(overrides)
    return StyleTaskRequest(**base)


def default_plans() -> list[ProductSearchPlan]:
    return [
        ProductSearchPlan(
            query="model selected short top",
            category=ProductCategory.top,
            colors=["ivory"],
            style_tags=["clean"],
            fit_tags=["short"],
        ),
        ProductSearchPlan(
            query="model selected high waist pants",
            category=ProductCategory.bottom,
            colors=["denim"],
            style_tags=["clean"],
            fit_tags=["high waist"],
        ),
        ProductSearchPlan(
            query="model selected simple shoes",
            category=ProductCategory.shoes,
            colors=["black"],
            style_tags=["simple"],
            fit_tags=["comfortable"],
        ),
    ]


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


class GoodPhotoProfileProvider:
    async def analyze(self, *, task_id, request):
        return StyleProfile(
            body_proportion="balanced",
            undertone="neutral",
            hair_tone="dark",
            style_signals=["model clean"],
            fit_advice=["model high waist"],
            palette=["ivory", "denim", "black"],
            photo_quality=PhotoQuality(
                is_full_body=True,
                face_visible=True,
                lighting="good",
                occlusion="low",
                resolution_score=0.9,
            ),
            confidence=0.9,
            summary="Model profile is usable.",
        )


class BadPhotoProfileProvider:
    async def analyze(self, *, task_id, request):
        return StyleProfile(
            body_proportion="balanced",
            undertone="neutral",
            hair_tone="dark",
            style_signals=["clean"],
            fit_advice=["high waist"],
            palette=["ivory", "black"],
            photo_quality=PhotoQuality(
                is_full_body=False,
                face_visible=False,
                lighting="poor",
                occlusion="high",
                resolution_score=0.3,
            ),
            confidence=0.4,
            summary="Photo quality is not usable.",
        )


class StaticQueryPlanner:
    source = "fake_model"

    def __init__(self, plans: list[ProductSearchPlan] | None = None) -> None:
        self.plans = plans or default_plans()

    async def build_queries(self, *, request, profile, constraints):
        return self.plans


class CatalogSearchProvider:
    source_id = "catalog_test"

    def __init__(self, empty: bool = False) -> None:
        self.empty = empty
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
        if self.empty:
            return []
        marketplace = marketplaces[0] if marketplaces else Marketplace.taobao
        product_id = f"{category.value}_{len(self.calls)}"
        return [
            ProductCandidate(
                product_id=product_id,
                marketplace=marketplace,
                source_provider=self.source_id,
                category=category,
                title=f"{query} marketplace title",
                price=199,
                price_text="199",
                image_url=f"https://img.alicdn.com/{product_id}.jpg",
                product_url=f"https://s.click.taobao.com/{product_id}",
                shop_name="Test shop",
                sizes=["S", "M", "L"],
                colors=colors,
                style_tags=style_tags,
                fit_tags=fit_tags,
                source_reliability=0.95,
                score=0.93,
            )
        ]


class ModelOutfitPlanner:
    source = "fake_outfit_model"

    def __init__(
        self,
        categories: list[ProductCategory] | None = None,
        *,
        score: float = 0.91,
        include_empty_plan: bool = False,
    ) -> None:
        self.categories = categories or [ProductCategory.top, ProductCategory.bottom, ProductCategory.shoes]
        self.score = score
        self.include_empty_plan = include_empty_plan

    async def build_outfits(self, *, request, profile, constraints, products):
        if self.include_empty_plan:
            return []
        selected: list[ProductCandidate] = []
        for category in self.categories:
            match = next((product for product in products if product.category == category), None)
            if match is not None:
                selected.append(match)
        if len(selected) != len(self.categories):
            return []
        return [
            ModelOutfitCandidatePlan(
                title="Model selected outfit",
                items=[
                    ModelOutfitItemPlan(
                        product_id=product.product_id,
                        selection_reason="Model selected this item for the outfit.",
                        match_reason="Model says this item fits the user and scene.",
                        selection_scores={"model": self.score},
                    )
                    for product in selected
                ],
                score=self.score,
                score_breakdown={
                    "fit": self.score,
                    "color": self.score,
                    "scene": self.score,
                    "budget": self.score,
                    "product_quality": self.score,
                },
                why_this_works=["Model reason one.", "Model reason two."],
            )
        ]


def graph_with_model_chain(
    *,
    tracer: InMemoryTraceRecorder,
    search_provider: CatalogSearchProvider | None = None,
    image_provider: TryOnImageProvider | None = None,
    photo_provider=None,
    query_planner: StaticQueryPlanner | None = None,
    outfit_planner: ModelOutfitPlanner | None = None,
    wardrobe_products=None,
) -> StyleAgentGraph:
    return StyleAgentGraph(
        settings=Settings(),
        tracer=tracer,
        search_provider=search_provider or CatalogSearchProvider(),
        image_provider=image_provider or LocalTryOnImageProvider(),
        photo_provider=photo_provider or GoodPhotoProfileProvider(),
        query_planner=query_planner or StaticQueryPlanner(),
        outfit_planner=outfit_planner or ModelOutfitPlanner(),
        wardrobe_products=wardrobe_products,
    )


class AgentGraphTests(unittest.IsolatedAsyncioTestCase):
    async def test_graph_returns_success_when_recommendation_and_image_pass(self) -> None:
        tracer = InMemoryTraceRecorder()
        graph = graph_with_model_chain(tracer=tracer)

        result = await graph.run(task_id="task_success", request=request())

        self.assertEqual(result.status, TaskStatus.succeeded)
        self.assertIsNotNone(result.outfit)
        self.assertIsNotNone(result.try_on_image_url)
        self.assertGreaterEqual(result.recommendation_report.final_score, 0.82)
        self.assertGreaterEqual(result.image_quality_report.overall_score, 0.84)
        self.assertGreater(len(tracer.by_task("task_success")), 5)

    async def test_low_quality_images_return_partial_result_with_best_tryon_candidate(self) -> None:
        tracer = InMemoryTraceRecorder()
        graph = graph_with_model_chain(tracer=tracer, image_provider=LowQualityImageProvider())

        result = await graph.run(task_id="task_partial", request=request())

        self.assertEqual(result.status, TaskStatus.partial_succeeded)
        self.assertIsNotNone(result.outfit)
        self.assertEqual(result.try_on_image_url, "https://generated.example.com/task_partial/bad-0-0.png")
        self.assertIsNotNone(result.image_quality_report)
        self.assertFalse(result.image_quality_report.accepted)

    async def test_bad_photo_quality_blocks_before_product_search(self) -> None:
        tracer = InMemoryTraceRecorder()
        search_provider = CatalogSearchProvider()
        graph = graph_with_model_chain(
            tracer=tracer,
            search_provider=search_provider,
            photo_provider=BadPhotoProfileProvider(),
        )

        result = await graph.run(task_id="task_bad_photo", request=request())

        self.assertEqual(result.status, TaskStatus.failed)
        self.assertIsNone(result.outfit)
        self.assertEqual(search_provider.calls, [])

    async def test_empty_product_data_surfaces_model_composition_exception(self) -> None:
        tracer = InMemoryTraceRecorder()
        graph = graph_with_model_chain(tracer=tracer, search_provider=CatalogSearchProvider(empty=True))

        with self.assertRaisesRegex(RuntimeError, "没有可供模型选择的商品"):
            await graph.run(task_id="task_empty_products", request=request())

    async def test_model_can_return_no_outfit_and_director_reports_failure(self) -> None:
        tracer = InMemoryTraceRecorder()
        graph = graph_with_model_chain(
            tracer=tracer,
            outfit_planner=ModelOutfitPlanner(include_empty_plan=True),
        )

        result = await graph.run(task_id="task_no_model_outfit", request=request())

        self.assertEqual(result.status, TaskStatus.failed)
        self.assertIsNone(result.try_on_image_url)

    async def test_fit_critic_preserves_model_scores_without_term_matching(self) -> None:
        from app.agents.fit_critic import FitCriticAgent
        from app.agents.state import StyleGraphState

        item = OutfitItem(
            product_id="model_item",
            marketplace=Marketplace.taobao,
            source_provider="test",
            category=ProductCategory.top,
            title="fixture title without preferred terms",
            price=129,
            price_text="129",
            image_url="https://img.alicdn.com/item.jpg",
            product_url="https://s.click.taobao.com/t",
            sizes=["S", "M", "L"],
            colors=["model-color"],
            style_tags=["model-style"],
            fit_tags=["model-fit"],
            source_reliability=0.94,
            score=0.94,
            selection_reason="Model selected this item.",
            match_reason="Model says this item matches.",
            selection_scores={"model": 0.94},
        )
        candidate = OutfitCandidate(
            candidate_id="outfit_model_score",
            title="Model scored outfit",
            items=[item],
            total_price=129,
            score=0.51,
            score_breakdown={"fit": 0.51},
            why_this_works=["Model reason one.", "Model reason two."],
        )
        state = StyleGraphState(
            task_id="task_fit_no_terms",
            request=request(),
            constraints=PreferenceConstraints(
                scene=Scene.daily,
                budget=Budget(min=300, max=900),
                positive_style_terms=["unmatched preference"],
                negative_style_terms=[],
                required_fit_terms=["unmatched fit"],
                palette=["unmatched color"],
                marketplaces=[Marketplace.taobao, Marketplace.tmall],
            ),
            outfit_candidates=[candidate],
        )

        reviewed = await FitCriticAgent(InMemoryTraceRecorder(), threshold=0.82).run(state)

        self.assertEqual(reviewed.outfit_candidates[0].score, 0.51)

    async def test_search_queries_can_come_from_model_planner(self) -> None:
        tracer = InMemoryTraceRecorder()
        search_provider = CatalogSearchProvider()
        graph = graph_with_model_chain(tracer=tracer, search_provider=search_provider)

        result = await graph.run(task_id="task_model_queries", request=request())

        self.assertEqual(result.status, TaskStatus.succeeded)
        scout_event = next(
            event for event in tracer.by_task("task_model_queries") if event["node"] == "ProductScoutAgent"
        )
        self.assertEqual(scout_event["payload"]["query_source"], "fake_model")
        self.assertEqual(scout_event["payload"]["queries"], [plan.model_dump() for plan in default_plans()])
        self.assertEqual(search_provider.calls[0]["category"], ProductCategory.top)
        self.assertEqual(search_provider.calls[0]["fit_tags"], ["short"])

    async def test_retry_image_reuses_approved_outfit_without_recommendation_search(self) -> None:
        tracer = InMemoryTraceRecorder()
        partial_graph = graph_with_model_chain(tracer=tracer, image_provider=LowQualityImageProvider())
        partial = await partial_graph.run(task_id="task_retry_source", request=request())
        self.assertEqual(partial.status, TaskStatus.partial_succeeded)
        self.assertIsNotNone(partial.outfit)

        retry_search_provider = CatalogSearchProvider(empty=True)
        retry_graph = StyleAgentGraph(
            settings=Settings(),
            tracer=tracer,
            search_provider=retry_search_provider,
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
        self.assertEqual(retry_search_provider.calls, [])

    async def test_wardrobe_items_are_added_to_product_pool_for_model_selection(self) -> None:
        tracer = InMemoryTraceRecorder()
        owned_outerwear = ProductCandidate(
            product_id="wardrobe_coat_1",
            marketplace=Marketplace.owned,
            category=ProductCategory.outerwear,
            title="Owned ivory blazer",
            price=0,
            price_text="owned",
            image_url="https://example.com/owned-coat.png",
            product_url="owned://wardrobe/wardrobe_coat_1",
            colors=["ivory"],
            style_tags=["commute", "clean"],
            fit_tags=["structured"],
            source_reliability=0.94,
            score=0.99,
        )
        graph = graph_with_model_chain(
            tracer=tracer,
            outfit_planner=ModelOutfitPlanner(
                [ProductCategory.outerwear, ProductCategory.top, ProductCategory.bottom, ProductCategory.shoes]
            ),
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
