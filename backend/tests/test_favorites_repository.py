from __future__ import annotations

from app.providers.persistence import InMemoryFavoritesRepository, InMemoryTaskRepository
from app.schemas.domain import (
    Budget,
    Marketplace,
    OutfitCandidate,
    OutfitItem,
    ProductCandidate,
    ProductCategory,
    Scene,
    StyleTaskRequest,
    TaskStatus,
)
from app.schemas.favorites import FavoriteProductCreate
from app.schemas.quality import GateStatus, QualityGateReport, RecommendationReport
from app.schemas.results import StyleTaskResult


def recommendation_report() -> RecommendationReport:
    return RecommendationReport(
        final_score=0.9,
        fit_score=0.9,
        color_score=0.9,
        occasion_score=0.9,
        budget_score=0.9,
        wardrobe_score=0.9,
        gates=[QualityGateReport(gate="recommendation", status=GateStatus.passed, score=0.9)],
        why_this_works=["complete outfit"],
    )


def product_candidate(product_id: str = "product-1", marketplace: Marketplace = Marketplace.taobao) -> ProductCandidate:
    return ProductCandidate(
        product_id=product_id,
        marketplace=marketplace,
        category=ProductCategory.top,
        title="Cotton shirt",
        price=199,
        price_text="CNY 199",
        image_url="https://example.com/shirt.jpg",
        product_url="https://example.com/products/shirt",
        shop_name="Example Shop",
        sizes=["M"],
        colors=["white"],
        style_tags=["clean"],
        fit_tags=["relaxed"],
        source_reliability=0.9,
        score=0.88,
    )


def outfit_candidate() -> OutfitCandidate:
    product = product_candidate()
    item = OutfitItem(
        **product.model_dump(),
        selection_reason="Works for the scene",
        match_reason="Pairs cleanly",
        selection_scores={"overall": 0.9},
    )
    return OutfitCandidate(
        candidate_id="outfit-1",
        title="Clean Daily Look",
        items=[item],
        total_price=199,
        score=0.9,
        score_breakdown={"overall": 0.9},
        why_this_works=["complete outfit"],
    )


def task_request() -> StyleTaskRequest:
    return StyleTaskRequest(
        photo_url="/uploads/person.jpg",
        photo_object_key="person.jpg",
        scene=Scene.daily,
        budget=Budget(min=100, max=500),
    )


def test_favorite_products_are_idempotent_and_scoped_by_user():
    repository = InMemoryFavoritesRepository()
    create = FavoriteProductCreate(**product_candidate().model_dump(), source_task_id="task-1")

    first = repository.save_product("user-1", create)
    second = repository.save_product("user-1", create)
    other_user = repository.save_product("user-2", create)

    assert second.favorite_id == first.favorite_id
    assert other_user.favorite_id != first.favorite_id
    assert [favorite.favorite_id for favorite in repository.list_products("user-1")] == [first.favorite_id]
    assert [favorite.favorite_id for favorite in repository.list_products("user-2")] == [other_user.favorite_id]
    assert repository.delete_product("user-2", first.favorite_id) is False
    assert repository.delete_product("user-1", first.favorite_id) is True
    assert repository.list_products("user-1") == []


def test_task_repository_stores_user_id_without_exposing_it_on_task_view():
    repository = InMemoryTaskRepository()

    task = repository.create("task-1", task_request(), user_id="user-1")

    assert repository.owner_id("task-1") == "user-1"
    assert task.owner_id is None
    assert not hasattr(task, "user_id")


def test_saved_looks_are_idempotent_and_scoped_by_user():
    task_repository = InMemoryTaskRepository()
    favorites_repository = InMemoryFavoritesRepository()
    task = task_repository.create("task-1", task_request(), user_id="user-1")
    completed = task_repository.complete(
        task.task_id,
        StyleTaskResult(
            task_id=task.task_id,
            status=TaskStatus.succeeded,
            outfit=outfit_candidate(),
            try_on_image_url="/try-on/task-1.jpg",
            recommendation_report=recommendation_report(),
        ),
    )

    first = favorites_repository.save_look("user-1", completed)
    second = favorites_repository.save_look("user-1", completed)
    other_user = favorites_repository.save_look("user-2", completed)

    assert second.look_id == first.look_id
    assert other_user.look_id != first.look_id
    assert [look.look_id for look in favorites_repository.list_looks("user-1")] == [first.look_id]
    assert [look.look_id for look in favorites_repository.list_looks("user-2")] == [other_user.look_id]
    assert first.source_task_id == "task-1"
    assert first.outfit == completed.result.outfit
    assert first.recommendation_report == recommendation_report()
    assert first.try_on_image_url == "/try-on/task-1.jpg"


def test_saved_look_snapshots_task_result_fields():
    task_repository = InMemoryTaskRepository()
    favorites_repository = InMemoryFavoritesRepository()
    task = task_repository.create("task-1", task_request(), user_id="user-1")
    completed = task_repository.complete(
        task.task_id,
        StyleTaskResult(
            task_id=task.task_id,
            status=TaskStatus.succeeded,
            outfit=outfit_candidate(),
            try_on_image_url="/try-on/task-1.jpg",
            recommendation_report=recommendation_report(),
        ),
    )

    saved = favorites_repository.save_look("user-1", completed)
    assert completed.result is not None
    assert completed.result.recommendation_report is not None
    assert completed.result.outfit is not None

    completed.result.recommendation_report.why_this_works.append("later mutation")
    completed.result.outfit.title = "Mutated Look"

    assert saved.recommendation_report.why_this_works == ["complete outfit"]
    assert saved.outfit is not None
    assert saved.outfit.title == "Clean Daily Look"
