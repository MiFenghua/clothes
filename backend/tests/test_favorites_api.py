from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.providers.auth import GoogleProfile
from app.providers.google_auth import GoogleIdTokenVerifier
from app.schemas.domain import Budget, Marketplace, OutfitCandidate, OutfitItem, ProductCategory, ProductCandidate, Scene, StyleTaskRequest, TaskStatus
from app.schemas.quality import GateStatus, QualityGateReport, RecommendationReport
from app.schemas.results import StyleTaskResult
from app.services.container import get_container


def google_profile(**overrides: object) -> GoogleProfile:
    data = {
        "sub": "google-sub-1",
        "email": "style.user@example.com",
        "email_verified": True,
        "name": "Style User",
        "avatar_url": "https://example.com/avatar.png",
    }
    data.update(overrides)
    return GoogleProfile(**data)


class FakeGoogleVerifier(GoogleIdTokenVerifier):
    def __init__(self) -> None:
        self.profile = google_profile()

    def verify(self, id_token: str) -> GoogleProfile:
        return self.profile


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


def product_candidate(product_id: str = "product-1") -> ProductCandidate:
    return ProductCandidate(
        product_id=product_id,
        marketplace=Marketplace.taobao,
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


def favorites_client(tmp_path, monkeypatch) -> tuple[TestClient, FakeGoogleVerifier]:
    storage_dir = tmp_path / "storage"
    monkeypatch.setenv("STYLE_BACKEND_STORAGE_DIR", str(storage_dir))
    monkeypatch.setenv("STYLE_BACKEND_GENERATED_DIR", str(storage_dir / "generated"))
    monkeypatch.setenv("STYLE_BACKEND_UPLOAD_DIR", str(storage_dir / "uploads"))
    monkeypatch.setenv("STYLE_BACKEND_AUTH_STORE_PATH", str(tmp_path / "auth-store.json"))
    monkeypatch.setenv("STYLE_BACKEND_PRODUCT_STORE_PATH", str(tmp_path / "product-store.json"))
    monkeypatch.setenv("STYLE_BACKEND_SEARCH_PROVIDER", "local_demo")
    monkeypatch.setenv("STYLE_BACKEND_POSTGRES_DSN", "memory")
    get_settings.cache_clear()
    get_container.cache_clear()

    from app.main import create_app

    container = get_container()
    verifier = FakeGoogleVerifier()
    container.google_id_token_verifier = verifier
    client = TestClient(create_app())
    return client, verifier


def login(client: TestClient, verifier: FakeGoogleVerifier, **overrides: object) -> dict[str, str]:
    verifier.profile = google_profile(**overrides)
    response = client.post("/api/v1/auth/google", json={"id_token": "header.payload.signature"})
    assert response.status_code == 200
    body = response.json()
    return {
        "user_id": body["user"]["user_id"],
        "token": body["session"]["token"],
    }


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def complete_task(
    user_id: str,
    *,
    status: TaskStatus,
    outfit: OutfitCandidate | None,
    report: RecommendationReport | None,
) -> str:
    container = get_container()
    task = container.task_service.create_task(task_request(), owner_id=user_id)
    container.task_service.repository.complete(
        task.task_id,
        StyleTaskResult(
            task_id=task.task_id,
            status=status,
            outfit=outfit,
            try_on_image_url="/try-on/task-1.jpg",
            recommendation_report=report,
        ),
    )
    return task.task_id


def test_get_favorite_products_requires_authentication(tmp_path, monkeypatch):
    client, _ = favorites_client(tmp_path, monkeypatch)

    response = client.get("/api/v1/favorite-products")

    assert response.status_code == 401
    assert response.json() == {"detail": "Authentication is required"}


def test_post_favorite_products_requires_authentication(tmp_path, monkeypatch):
    client, _ = favorites_client(tmp_path, monkeypatch)

    response = client.post("/api/v1/favorite-products", json=product_candidate().model_dump(mode="json"))

    assert response.status_code == 401
    assert response.json() == {"detail": "Authentication is required"}


def test_delete_favorite_products_requires_authentication(tmp_path, monkeypatch):
    client, _ = favorites_client(tmp_path, monkeypatch)

    response = client.delete("/api/v1/favorite-products/favorite_missing")

    assert response.status_code == 401
    assert response.json() == {"detail": "Authentication is required"}


def test_favorite_products_create_list_delete_and_duplicate_is_idempotent(tmp_path, monkeypatch):
    client, verifier = favorites_client(tmp_path, monkeypatch)
    login_data = login(client, verifier)
    payload = product_candidate().model_dump(mode="json")

    create_response = client.post("/api/v1/favorite-products", json=payload, headers=auth_headers(login_data["token"]))
    duplicate_response = client.post(
        "/api/v1/favorite-products",
        json=payload,
        headers=auth_headers(login_data["token"]),
    )
    list_response = client.get("/api/v1/favorite-products", headers=auth_headers(login_data["token"]))

    assert create_response.status_code == 201
    favorite = create_response.json()
    assert favorite["product_id"] == payload["product_id"]
    assert favorite["price_text"] == "CNY 199"

    assert duplicate_response.status_code == 200
    assert duplicate_response.json()["favorite_id"] == favorite["favorite_id"]

    assert list_response.status_code == 200
    assert [item["favorite_id"] for item in list_response.json()] == [favorite["favorite_id"]]

    delete_response = client.delete(
        f"/api/v1/favorite-products/{favorite['favorite_id']}",
        headers=auth_headers(login_data["token"]),
    )
    empty_response = client.get("/api/v1/favorite-products", headers=auth_headers(login_data["token"]))

    assert delete_response.status_code == 200
    assert delete_response.json() == {"ok": True}
    assert empty_response.status_code == 200
    assert empty_response.json() == []


def test_favorite_products_are_scoped_to_the_current_user(tmp_path, monkeypatch):
    client, verifier = favorites_client(tmp_path, monkeypatch)
    first_login = login(client, verifier)
    second_login = login(client, verifier, sub="google-sub-2", email="second@example.com", name="Second User")

    create_response = client.post(
        "/api/v1/favorite-products",
        json=product_candidate().model_dump(mode="json"),
        headers=auth_headers(first_login["token"]),
    )
    assert create_response.status_code == 201
    favorite_id = create_response.json()["favorite_id"]

    second_list_response = client.get("/api/v1/favorite-products", headers=auth_headers(second_login["token"]))
    wrong_owner_delete_response = client.delete(
        f"/api/v1/favorite-products/{favorite_id}",
        headers=auth_headers(second_login["token"]),
    )
    first_list_response = client.get("/api/v1/favorite-products", headers=auth_headers(first_login["token"]))

    assert second_list_response.status_code == 200
    assert second_list_response.json() == []
    assert wrong_owner_delete_response.status_code == 404
    assert wrong_owner_delete_response.json() == {"detail": "Favorite product not found"}
    assert [item["favorite_id"] for item in first_list_response.json()] == [favorite_id]


def test_favorite_product_rejects_another_users_source_task(tmp_path, monkeypatch):
    client, verifier = favorites_client(tmp_path, monkeypatch)
    first_login = login(client, verifier)
    second_login = login(client, verifier, sub="google-sub-2", email="second@example.com", name="Second User")
    source_task_id = complete_task(
        first_login["user_id"],
        status=TaskStatus.succeeded,
        outfit=outfit_candidate(),
        report=recommendation_report(),
    )

    payload = product_candidate().model_dump(mode="json")
    payload["source_task_id"] = source_task_id
    response = client.post("/api/v1/favorite-products", json=payload, headers=auth_headers(second_login["token"]))

    assert response.status_code == 404
    assert response.json() == {"detail": "Task not found"}


def test_save_look_returns_not_found_for_missing_task(tmp_path, monkeypatch):
    client, verifier = favorites_client(tmp_path, monkeypatch)
    login_data = login(client, verifier)

    response = client.post(
        "/api/v1/style-tasks/task_missing/save-look",
        headers=auth_headers(login_data["token"]),
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Task not found"}


def test_save_look_returns_conflict_when_task_has_no_completed_outfit(tmp_path, monkeypatch):
    client, verifier = favorites_client(tmp_path, monkeypatch)
    login_data = login(client, verifier)
    task_id = complete_task(
        login_data["user_id"],
        status=TaskStatus.succeeded,
        outfit=None,
        report=recommendation_report(),
    )

    response = client.post(
        f"/api/v1/style-tasks/{task_id}/save-look",
        headers=auth_headers(login_data["token"]),
    )

    assert response.status_code == 409
    assert response.json() == {"detail": "Task has no completed look to save"}


def test_save_look_rejects_failed_task_even_with_outfit_and_report(tmp_path, monkeypatch):
    client, verifier = favorites_client(tmp_path, monkeypatch)
    login_data = login(client, verifier)
    task_id = complete_task(
        login_data["user_id"],
        status=TaskStatus.failed,
        outfit=outfit_candidate(),
        report=recommendation_report(),
    )

    response = client.post(
        f"/api/v1/style-tasks/{task_id}/save-look",
        headers=auth_headers(login_data["token"]),
    )

    assert response.status_code == 409
    assert response.json() == {"detail": "Task has no completed look to save"}


@pytest.mark.parametrize("task_status", [TaskStatus.partial_succeeded, TaskStatus.succeeded])
def test_save_look_is_idempotent_and_lists_saved_looks(tmp_path, monkeypatch, task_status):
    client, verifier = favorites_client(tmp_path, monkeypatch)
    login_data = login(client, verifier)
    task_id = complete_task(
        login_data["user_id"],
        status=task_status,
        outfit=outfit_candidate(),
        report=recommendation_report(),
    )

    first_response = client.post(
        f"/api/v1/style-tasks/{task_id}/save-look",
        headers=auth_headers(login_data["token"]),
    )
    second_response = client.post(
        f"/api/v1/style-tasks/{task_id}/save-look",
        headers=auth_headers(login_data["token"]),
    )
    list_response = client.get("/api/v1/saved-looks", headers=auth_headers(login_data["token"]))

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    first_saved = first_response.json()
    second_saved = second_response.json()
    assert second_saved["look_id"] == first_saved["look_id"]
    assert first_saved["source_task_id"] == task_id
    assert first_saved["outfit"]["title"] == "Clean Daily Look"
    assert first_saved["recommendation_report"]["why_this_works"] == ["complete outfit"]

    assert list_response.status_code == 200
    assert [item["look_id"] for item in list_response.json()] == [first_saved["look_id"]]


def test_get_saved_looks_requires_authentication(tmp_path, monkeypatch):
    client, _ = favorites_client(tmp_path, monkeypatch)

    response = client.get("/api/v1/saved-looks")

    assert response.status_code == 401
    assert response.json() == {"detail": "Authentication is required"}


def test_save_look_requires_authentication(tmp_path, monkeypatch):
    client, _ = favorites_client(tmp_path, monkeypatch)

    response = client.post("/api/v1/style-tasks/task_missing/save-look")

    assert response.status_code == 401
    assert response.json() == {"detail": "Authentication is required"}
