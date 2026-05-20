from __future__ import annotations

import inspect
import os
from pathlib import Path

import pytest

from app.providers.auth import GoogleProfile
from app.schemas.domain import (
    Budget,
    Marketplace,
    OutfitCandidate,
    OutfitItem,
    ProductCategory,
    Scene,
    StyleTaskRequest,
    TaskStatus,
    WardrobeItem,
)
from app.schemas.favorites import FavoriteProductCreate
from app.schemas.quality import GateStatus, QualityGateReport, RecommendationReport
from app.schemas.results import StyleTaskResult


POSTGRES_DSN = os.getenv("STYLE_BACKEND_TEST_POSTGRES_DSN")


def test_postgres_auth_upsert_uses_conflict_handling():
    from app.providers.postgres import PostgresAuthStore

    source = inspect.getsource(PostgresAuthStore.upsert_google_user)

    assert "ON CONFLICT" in source
    assert "_find_user_by_google_sub" not in source
    assert "_find_user_by_email" not in source


def test_postgres_saved_look_uses_conflict_handling():
    from app.providers.postgres import PostgresFavoritesRepository

    source = inspect.getsource(PostgresFavoritesRepository.save_look)

    assert "ON CONFLICT" in source
    assert "SELECT *\n                FROM saved_looks" not in source


def apply_migration_and_reset(dsn: str) -> None:
    import psycopg

    migration_sql = (Path(__file__).parents[1] / "migrations" / "001_initial.sql").read_text(encoding="utf-8")
    truncate_sql = """
        TRUNCATE
          favorite_products,
          saved_looks,
          trace_events,
          wardrobe_items,
          style_tasks,
          auth_sessions,
          auth_users
        RESTART IDENTITY CASCADE
    """
    with psycopg.connect(dsn) as conn:
        conn.execute(migration_sql)
        conn.execute(truncate_sql)


@pytest.fixture()
def postgres_db():
    if POSTGRES_DSN is None:
        pytest.skip("STYLE_BACKEND_TEST_POSTGRES_DSN is not set")

    from app.providers.postgres import PostgresDatabase

    apply_migration_and_reset(POSTGRES_DSN)
    return PostgresDatabase(POSTGRES_DSN)


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


def task_request() -> StyleTaskRequest:
    return StyleTaskRequest(
        photo_url="/uploads/person.jpg",
        photo_object_key="person.jpg",
        scene=Scene.daily,
        budget=Budget(min=100, max=500),
        wardrobe_item_ids=["wardrobe-1"],
        marketplaces=[Marketplace.taobao, Marketplace.jd],
    )


def favorite_product(
    product_id: str = "product-1",
    marketplace: Marketplace = Marketplace.taobao,
) -> FavoriteProductCreate:
    return FavoriteProductCreate(
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
        source_task_id="task-1",
    )


def outfit_candidate() -> OutfitCandidate:
    product = favorite_product()
    item = OutfitItem(
        **product.model_dump(exclude={"source_task_id"}),
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


def test_auth_store_persists_google_users_sessions_and_invalidates_tokens(postgres_db):
    from app.providers.postgres import PostgresAuthStore

    store = PostgresAuthStore(postgres_db, session_max_age_days=30)
    user = store.upsert_google_user(
        GoogleProfile(
            sub="google-sub-1",
            email=" USER@Example.COM ",
            email_verified=True,
            name="Example User",
            avatar_url="https://example.com/avatar.jpg",
        )
    )
    session = store.create_session(user.user_id)

    assert user.email == "user@example.com"
    assert store.get_user_by_token(session.token).user_id == user.user_id

    reloaded = PostgresAuthStore(postgres_db, session_max_age_days=30)
    assert reloaded.get_user_by_token(session.token).email == "user@example.com"

    reloaded.destroy_session(session.token)
    assert reloaded.get_user_by_token(session.token) is None


def test_task_trace_and_wardrobe_repositories_persist_and_reload(postgres_db):
    from app.providers.postgres import (
        PostgresAuthStore,
        PostgresTaskRepository,
        PostgresTraceRecorder,
        PostgresWardrobeRepository,
    )

    auth_store = PostgresAuthStore(postgres_db, session_max_age_days=30)
    user = auth_store.upsert_google_user(
        GoogleProfile(sub="google-sub-1", email="user@example.com", email_verified=True, name="User")
    )
    task_repository = PostgresTaskRepository(postgres_db)
    wardrobe_repository = PostgresWardrobeRepository(postgres_db)
    tracer = PostgresTraceRecorder(postgres_db)

    item = wardrobe_repository.save(
        WardrobeItem(
            item_id="wardrobe-1",
            owner_id=user.user_id,
            category=ProductCategory.top,
            title="Owned cotton shirt",
            image_url="https://example.com/owned-shirt.jpg",
            colors=["white"],
            style_tags=["clean"],
            fit_tags=["relaxed"],
            notes="Already in closet",
        )
    )
    created = task_repository.create("task-1", task_request(), user_id=user.user_id)
    updated = task_repository.update_status("task-1", TaskStatus.scouting_products, "Scouting", 40)
    completed = task_repository.complete(
        "task-1",
        StyleTaskResult(
            task_id="task-1",
            status=TaskStatus.succeeded,
            outfit=outfit_candidate(),
            try_on_image_url="/try-on/task-1.jpg",
            recommendation_report=recommendation_report(),
        ),
    )
    tracer.record("task-1", "node-a", "started", {"ok": True})

    reloaded = PostgresTaskRepository(postgres_db).get("task-1")
    recent = task_repository.list_recent_completed(owner_id=user.user_id, limit=3)
    wardrobe_items = PostgresWardrobeRepository(postgres_db).list_for_user(user.user_id)
    products = wardrobe_repository.products_for_ids([item.item_id, "missing"])
    trace_events = PostgresTraceRecorder(postgres_db).by_task("task-1")

    assert created.owner_id == user.user_id
    assert updated.status == TaskStatus.scouting_products
    assert completed.progress == 100
    assert task_repository.owner_id("task-1") == user.user_id
    assert reloaded.request == task_request()
    assert reloaded.result is not None
    assert reloaded.result.recommendation_report == recommendation_report()
    assert [task.task_id for task in recent] == ["task-1"]
    assert wardrobe_items == [item]
    assert products[0].marketplace == Marketplace.owned
    assert products[0].price == 0
    assert products[0].price_text == "Owned wardrobe"
    assert products[0].product_url == "owned://wardrobe/wardrobe-1"
    assert trace_events == [
        {
            "timestamp": trace_events[0]["timestamp"],
            "task_id": "task-1",
            "node": "node-a",
            "event": "started",
            "payload": {"ok": True},
        }
    ]


def test_favorites_repository_is_idempotent_scoped_and_supports_nullable_saved_look_outfit(postgres_db):
    from app.providers.postgres import PostgresAuthStore, PostgresFavoritesRepository, PostgresTaskRepository

    auth_store = PostgresAuthStore(postgres_db, session_max_age_days=30)
    user_1 = auth_store.upsert_google_user(
        GoogleProfile(sub="google-sub-1", email="user1@example.com", email_verified=True, name="User 1")
    )
    user_2 = auth_store.upsert_google_user(
        GoogleProfile(sub="google-sub-2", email="user2@example.com", email_verified=True, name="User 2")
    )
    task_repository = PostgresTaskRepository(postgres_db)
    task = task_repository.create("task-1", task_request(), user_id=user_1.user_id)
    completed = task_repository.complete(
        task.task_id,
        StyleTaskResult(
            task_id=task.task_id,
            status=TaskStatus.succeeded,
            outfit=None,
            try_on_image_url="/try-on/task-1.jpg",
            recommendation_report=recommendation_report(),
        ),
    )
    favorites = PostgresFavoritesRepository(postgres_db)
    product = favorite_product()

    first = favorites.save_product(user_1.user_id, product)
    second = favorites.save_product(user_1.user_id, product)
    other_user = favorites.save_product(user_2.user_id, product)
    first_look = favorites.save_look(user_1.user_id, completed)
    second_look = favorites.save_look(user_1.user_id, completed)
    other_user_look = favorites.save_look(user_2.user_id, completed)

    assert second.favorite_id == first.favorite_id
    assert other_user.favorite_id != first.favorite_id
    assert [favorite.favorite_id for favorite in favorites.list_products(user_1.user_id)] == [first.favorite_id]
    assert [favorite.favorite_id for favorite in favorites.list_products(user_2.user_id)] == [other_user.favorite_id]
    assert favorites.delete_product(user_2.user_id, first.favorite_id) is False
    assert favorites.delete_product(user_1.user_id, first.favorite_id) is True
    assert favorites.list_products(user_1.user_id) == []

    assert second_look.look_id == first_look.look_id
    assert other_user_look.look_id != first_look.look_id
    assert first_look.outfit is None
    assert first_look.recommendation_report == recommendation_report()
    assert [look.look_id for look in favorites.list_looks(user_1.user_id)] == [first_look.look_id]
    assert [look.look_id for look in favorites.list_looks(user_2.user_id)] == [other_user_look.look_id]


def test_task_repository_rejects_owner_mismatch(postgres_db):
    from app.providers.postgres import PostgresTaskRepository

    repository = PostgresTaskRepository(postgres_db)

    with pytest.raises(ValueError, match="Task owner mismatch"):
        repository.create("task-bad", task_request(), user_id="a", owner_id="b")
