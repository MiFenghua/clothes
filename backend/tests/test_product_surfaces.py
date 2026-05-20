from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.main import create_app
from app.providers.auth import AuthStore, GoogleProfile
from app.providers.google_auth import GoogleIdTokenVerifier
from app.providers import product_content
from app.providers.product_content import FavoriteRepository, ProfileRepository
from app.schemas.domain import Budget, OutfitCandidate, Scene, StyleTaskRequest, TaskStatus
from app.schemas.product import FavoriteCreate, FavoriteType, StyleProfileUpdate
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


def product_client(tmp_path) -> TestClient:
    get_container.cache_clear()
    container = get_container()
    container.settings.auth_store_path = tmp_path / "product-auth.json"
    container.auth_store = AuthStore(container.settings.auth_store_path, session_max_age_days=30)
    return TestClient(create_app())


def authenticated_product_client(tmp_path) -> tuple[TestClient, FakeGoogleVerifier]:
    get_container.cache_clear()
    container = get_container()
    container.settings.auth_store_path = tmp_path / "product-auth.json"
    container.auth_store = AuthStore(container.settings.auth_store_path, session_max_age_days=30)
    verifier = FakeGoogleVerifier()
    container.google_id_token_verifier = verifier
    return TestClient(create_app()), verifier


def test_profile_returns_anonymous_default(tmp_path):
    client = product_client(tmp_path)

    response = client.get("/api/v1/profile")

    assert response.status_code == 200
    body = response.json()
    assert body["user"] is None
    assert body["style_profile"]["display_name"] == "Style User"
    assert body["style_profile"]["feature_metrics"][0]["label"] == "Height"
    assert "clean" in body["style_profile"]["style_keywords"]


def test_anonymous_style_profile_update_is_not_persisted(tmp_path):
    client = product_client(tmp_path)

    response = client.put(
        "/api/v1/profile/style",
        json={"height_cm": 177, "body_shape": "hourglass", "skin_tone": "cool", "hair_tone": "black"},
    )

    assert response.status_code == 200
    body = response.json()
    metrics = {metric["label"]: metric["value"] for metric in body["feature_metrics"]}
    assert body["height_cm"] == 177
    assert body["body_shape"] == "hourglass"
    assert body["feature_metrics"][0]["label"] == "Height"
    assert metrics["Height"] == "177 cm"
    assert metrics["Body shape"] == "hourglass"
    assert metrics["Skin tone"] == "cool"
    assert metrics["Hair tone"] == "black"

    get_response = client.get("/api/v1/profile")

    assert get_response.status_code == 200
    profile = get_response.json()["style_profile"]
    get_metrics = {metric["label"]: metric["value"] for metric in profile["feature_metrics"]}
    assert profile["height_cm"] == 168
    assert profile["body_shape"] == "balanced"
    assert get_metrics["Height"] == "168 cm"
    assert get_metrics["Body shape"] == "balanced"


def test_authenticated_style_profile_update_persists(tmp_path):
    client, _ = authenticated_product_client(tmp_path)
    login_response = client.post("/api/v1/auth/google", json={"id_token": "header.payload.signature"})
    assert login_response.status_code == 200
    token = login_response.json()["session"]["token"]

    update_response = client.put(
        "/api/v1/profile/style",
        json={"height_cm": 175, "body_shape": "straight", "skin_tone": "cool", "hair_tone": "black"},
        headers={"Authorization": f"Bearer {token}"},
    )
    get_response = client.get("/api/v1/profile", headers={"Authorization": f"Bearer {token}"})

    assert update_response.status_code == 200
    assert get_response.status_code == 200
    profile = get_response.json()["style_profile"]
    metrics = {metric["label"]: metric["value"] for metric in profile["feature_metrics"]}
    assert profile["height_cm"] == 175
    assert profile["body_shape"] == "straight"
    assert metrics["Height"] == "175 cm"
    assert metrics["Body shape"] == "straight"


def test_home_returns_seeded_recommendations_without_tasks(tmp_path):
    client = product_client(tmp_path)

    response = client.get("/api/v1/home")

    assert response.status_code == 200
    body = response.json()
    assert body["feature_summary"]["score"] >= 0.8
    assert len(body["recommendations"]) >= 3
    assert body["today_suggestion"]["title"]
    assert body["backend_status"]["ok"] is True


def test_seeded_inspiration_image_urls_do_not_reference_missing_static_assets():
    static_root = Path(product_content.__file__).resolve().parents[1] / "static"

    missing = [
        look.image_url
        for look in product_content.SEEDED_INSPIRATIONS
        if look.image_url
        and look.image_url.startswith("/static/")
        and not (static_root / look.image_url.removeprefix("/static/")).exists()
    ]

    assert missing == []


def test_inspirations_can_filter_by_scene(tmp_path):
    client = product_client(tmp_path)

    response = client.get("/api/v1/inspirations?scene=commute")

    assert response.status_code == 200
    body = response.json()
    assert body["items"]
    assert {item["scene"] for item in body["items"]} == {"commute"}


def test_favorite_routes_require_authentication(tmp_path):
    client = product_client(tmp_path)

    list_response = client.get("/api/v1/favorites?type=inspiration")
    create_response = client.post(
        "/api/v1/favorites",
        json={
            "favorite_type": "inspiration",
            "target_id": "inspiration_commute_001",
            "snapshot": {"title": "Look"},
        },
    )
    delete_response = client.delete("/api/v1/favorites/favorite_missing")

    assert list_response.status_code == 401
    assert create_response.status_code == 401
    assert delete_response.status_code == 401


def test_favorite_routes_round_trip_for_authenticated_user(tmp_path):
    client, _ = authenticated_product_client(tmp_path)
    login_response = client.post("/api/v1/auth/google", json={"id_token": "header.payload.signature"})
    assert login_response.status_code == 200
    token = login_response.json()["session"]["token"]
    owner_id = login_response.json()["user"]["user_id"]
    headers = {"Authorization": f"Bearer {token}"}

    create_response = client.post(
        "/api/v1/favorites",
        json={
            "favorite_type": "inspiration",
            "target_id": "inspiration_commute_001",
            "snapshot": {"title": "Soft Tailored Commute"},
        },
        headers=headers,
    )

    assert create_response.status_code == 200
    favorite = create_response.json()
    assert favorite["favorite_id"]
    assert favorite["owner_id"] == owner_id
    assert favorite["target_id"] == "inspiration_commute_001"

    list_response = client.get("/api/v1/favorites?type=inspiration", headers=headers)
    assert list_response.status_code == 200
    favorites = list_response.json()
    assert len(favorites) == 1
    assert favorites[0]["favorite_id"] == favorite["favorite_id"]

    update_response = client.post(
        "/api/v1/favorites",
        json={
            "favorite_type": "inspiration",
            "target_id": "inspiration_commute_001",
            "snapshot": {"title": "Updated Commute"},
        },
        headers=headers,
    )
    assert update_response.status_code == 200
    updated_favorite = update_response.json()
    assert updated_favorite["favorite_id"] == favorite["favorite_id"]
    assert updated_favorite["snapshot"] == {"title": "Updated Commute"}

    inspirations_response = client.get("/api/v1/inspirations?scene=commute", headers=headers)
    assert inspirations_response.status_code == 200
    inspirations_by_id = {item["inspiration_id"]: item for item in inspirations_response.json()["items"]}
    assert inspirations_by_id["inspiration_commute_001"]["favorite_id"] == favorite["favorite_id"]

    delete_response = client.delete(f"/api/v1/favorites/{favorite['favorite_id']}", headers=headers)
    assert delete_response.status_code == 200
    assert delete_response.json() == {"ok": True}

    empty_response = client.get("/api/v1/favorites?type=inspiration", headers=headers)
    assert empty_response.status_code == 200
    assert empty_response.json() == []


def test_favorite_routes_are_scoped_between_users(tmp_path):
    client, verifier = authenticated_product_client(tmp_path)
    first_login_response = client.post("/api/v1/auth/google", json={"id_token": "header.payload.signature"})
    assert first_login_response.status_code == 200
    first_token = first_login_response.json()["session"]["token"]
    first_headers = {"Authorization": f"Bearer {first_token}"}

    create_response = client.post(
        "/api/v1/favorites",
        json={
            "favorite_type": "inspiration",
            "target_id": "inspiration_commute_001",
            "snapshot": {"title": "Soft Tailored Commute"},
        },
        headers=first_headers,
    )
    assert create_response.status_code == 200
    favorite_id = create_response.json()["favorite_id"]

    verifier.profile = google_profile(sub="google-sub-2", email="second@example.com", name="Second User")
    second_login_response = client.post("/api/v1/auth/google", json={"id_token": "header.payload.signature"})
    assert second_login_response.status_code == 200
    second_token = second_login_response.json()["session"]["token"]
    second_headers = {"Authorization": f"Bearer {second_token}"}

    second_list_response = client.get("/api/v1/favorites?type=inspiration", headers=second_headers)
    assert second_list_response.status_code == 200
    assert second_list_response.json() == []

    second_inspirations_response = client.get("/api/v1/inspirations?scene=commute", headers=second_headers)
    assert second_inspirations_response.status_code == 200
    inspirations_by_id = {item["inspiration_id"]: item for item in second_inspirations_response.json()["items"]}
    assert inspirations_by_id["inspiration_commute_001"]["favorite_id"] is None

    wrong_owner_delete_response = client.delete(f"/api/v1/favorites/{favorite_id}", headers=second_headers)
    assert wrong_owner_delete_response.status_code == 404

    first_list_response = client.get("/api/v1/favorites?type=inspiration", headers=first_headers)
    assert first_list_response.status_code == 200
    assert [favorite["favorite_id"] for favorite in first_list_response.json()] == [favorite_id]


def test_favorite_routes_reject_invalid_bearer_like_anonymous(tmp_path):
    client = product_client(tmp_path)

    response = client.get("/api/v1/favorites?type=inspiration", headers={"Authorization": "Bearer missing-token"})

    assert response.status_code == 401


def test_favorite_save_is_idempotent_for_owner_type_and_target():
    repository = FavoriteRepository()
    create = FavoriteCreate(
        favorite_type=FavoriteType.inspiration,
        target_id="inspiration_commute_001",
        snapshot={"title": "Original"},
    )

    first = repository.save("owner-1", create)
    second = repository.save(
        "owner-1",
        FavoriteCreate(
            favorite_type=FavoriteType.inspiration,
            target_id="inspiration_commute_001",
            snapshot={"title": "Updated"},
        ),
    )

    assert second.favorite_id == first.favorite_id
    assert second.snapshot == {"title": "Updated"}
    assert len(repository.list_for_owner("owner-1")) == 1


def test_anonymous_favorite_save_is_rejected_and_list_is_empty():
    repository = FavoriteRepository()
    create = FavoriteCreate(
        favorite_type=FavoriteType.inspiration,
        target_id="inspiration_commute_001",
    )

    try:
        repository.save(None, create)
    except PermissionError as exc:
        assert str(exc) == "Authentication is required for favorites"
    else:
        raise AssertionError("Expected PermissionError for anonymous favorite save")

    assert repository.list_for_owner(None) == []
    assert repository.list_for_owner(None, FavoriteType.inspiration) == []

    try:
        repository.delete(None, "favorite_missing")
    except KeyError:
        pass
    else:
        raise AssertionError("Expected KeyError for anonymous delete of missing favorite")


def test_favorite_delete_distinguishes_missing_from_wrong_owner():
    repository = FavoriteRepository()
    favorite = repository.save(
        "owner-1",
        FavoriteCreate(favorite_type=FavoriteType.inspiration, target_id="inspiration_commute_001"),
    )

    try:
        repository.delete("owner-2", favorite.favorite_id)
    except PermissionError:
        pass
    else:
        raise AssertionError("Expected PermissionError for another owner's favorite")

    try:
        repository.delete(None, favorite.favorite_id)
    except PermissionError:
        pass
    else:
        raise AssertionError("Expected PermissionError for anonymous favorite delete")
    assert repository.list_for_owner("owner-1") == [favorite]

    try:
        repository.delete("owner-1", "favorite_missing")
    except KeyError:
        pass
    else:
        raise AssertionError("Expected KeyError for a missing favorite")

    assert repository.delete("owner-1", favorite.favorite_id) is None
    assert repository.list_for_owner("owner-1") == []


def test_profile_update_recomputes_feature_metrics():
    repository = ProfileRepository()

    updated = repository.update(
        "owner-1",
        StyleProfileUpdate(height_cm=172, body_shape="petite", skin_tone="warm", hair_tone="black"),
        "Ada",
    )

    metrics = {metric.label: metric.value for metric in updated.feature_metrics}
    assert updated.feature_metrics[0].label == "Height"
    assert metrics["Height"] == "172 cm"
    assert metrics["Body shape"] == "petite"
    assert metrics["Skin tone"] == "warm"
    assert metrics["Hair tone"] == "black"


def test_home_uses_authenticated_recent_completed_task(tmp_path):
    client, _ = authenticated_product_client(tmp_path)
    login_response = client.post("/api/v1/auth/google", json={"id_token": "header.payload.signature"})
    assert login_response.status_code == 200
    token = login_response.json()["session"]["token"]
    owner_id = login_response.json()["user"]["user_id"]

    container = get_container()
    task = container.task_service.create_task(
        StyleTaskRequest(
            photo_url="/uploads/photo.jpg",
            photo_object_key="photo.jpg",
            scene=Scene.date,
            budget=Budget(min=300, max=800),
        ),
        owner_id=owner_id,
    )
    container.task_service.repository.complete(
        task.task_id,
        StyleTaskResult(
            task_id=task.task_id,
            status=TaskStatus.succeeded,
            outfit=OutfitCandidate(
                candidate_id="outfit_1",
                title="Task Backed Look",
                items=[],
                total_price=0,
                score=0.91,
                score_breakdown={"overall": 0.91},
                why_this_works=["recent task result"],
            ),
            try_on_image_url="/try-on/task-backed.jpg",
        ),
    )

    response = client.get("/api/v1/home", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    first = response.json()["recommendations"][0]
    assert first["source_task_id"] == task.task_id
    assert first["title"] == "Task Backed Look"
    assert first["scene"] == "date"


def test_anonymous_home_ignores_anonymous_completed_task_history(tmp_path):
    client = product_client(tmp_path)
    container = get_container()
    task = container.task_service.create_task(
        StyleTaskRequest(
            photo_url="/uploads/anonymous-photo.jpg",
            photo_object_key="anonymous-photo.jpg",
            scene=Scene.travel,
            budget=Budget(min=300, max=800),
        ),
        owner_id=None,
    )
    container.task_service.repository.complete(
        task.task_id,
        StyleTaskResult(
            task_id=task.task_id,
            status=TaskStatus.succeeded,
            outfit=OutfitCandidate(
                candidate_id="outfit_anonymous",
                title="Anonymous Task Look",
                items=[],
                total_price=0,
                score=0.9,
                score_breakdown={"overall": 0.9},
                why_this_works=["anonymous task result"],
            ),
        ),
    )

    response = client.get("/api/v1/home")

    assert response.status_code == 200
    recommendations = response.json()["recommendations"]
    assert task.task_id not in {item["source_task_id"] for item in recommendations}
    assert "Anonymous Task Look" not in {item["title"] for item in recommendations}


def test_home_history_is_scoped_to_current_user(tmp_path):
    client, verifier = authenticated_product_client(tmp_path)
    first_login_response = client.post("/api/v1/auth/google", json={"id_token": "header.payload.signature"})
    assert first_login_response.status_code == 200
    first_login = first_login_response.json()
    first_token = first_login["session"]["token"]
    first_user_id = first_login["user"]["user_id"]

    verifier.profile = google_profile(sub="google-sub-2", email="second@example.com", name="Second User")
    second_login_response = client.post("/api/v1/auth/google", json={"id_token": "header.payload.signature"})
    assert second_login_response.status_code == 200
    second_token = second_login_response.json()["session"]["token"]

    container = get_container()
    task = container.task_service.create_task(
        StyleTaskRequest(
            photo_url="/uploads/private-photo.jpg",
            photo_object_key="private-photo.jpg",
            scene=Scene.commute,
            budget=Budget(min=300, max=800),
        ),
        owner_id=first_user_id,
    )
    container.task_service.repository.complete(
        task.task_id,
        StyleTaskResult(
            task_id=task.task_id,
            status=TaskStatus.succeeded,
            outfit=OutfitCandidate(
                candidate_id="outfit_private",
                title="Private User A Look",
                items=[],
                total_price=0,
                score=0.93,
                score_breakdown={"overall": 0.93},
                why_this_works=["belongs to user A"],
            ),
        ),
    )

    anonymous_home_response = client.get("/api/v1/home")
    second_home_response = client.get("/api/v1/home", headers={"Authorization": f"Bearer {second_token}"})
    first_home_response = client.get("/api/v1/home", headers={"Authorization": f"Bearer {first_token}"})

    assert anonymous_home_response.status_code == 200
    anonymous_recommendations = anonymous_home_response.json()["recommendations"]
    assert task.task_id not in {item["source_task_id"] for item in anonymous_recommendations}
    assert "Private User A Look" not in {item["title"] for item in anonymous_recommendations}

    assert second_home_response.status_code == 200
    second_recommendations = second_home_response.json()["recommendations"]
    assert task.task_id not in {item["source_task_id"] for item in second_recommendations}
    assert "Private User A Look" not in {item["title"] for item in second_recommendations}

    assert first_home_response.status_code == 200
    first_recommendations = first_home_response.json()["recommendations"]
    assert task.task_id in {item["source_task_id"] for item in first_recommendations}
    assert "Private User A Look" in {item["title"] for item in first_recommendations}


def test_style_task_read_is_scoped_to_owner(tmp_path):
    client, verifier = authenticated_product_client(tmp_path)
    first_login_response = client.post("/api/v1/auth/google", json={"id_token": "header.payload.signature"})
    assert first_login_response.status_code == 200
    first_token = first_login_response.json()["session"]["token"]
    first_user_id = first_login_response.json()["user"]["user_id"]

    verifier.profile = google_profile(sub="google-sub-2", email="second@example.com", name="Second User")
    second_login_response = client.post("/api/v1/auth/google", json={"id_token": "header.payload.signature"})
    assert second_login_response.status_code == 200
    second_token = second_login_response.json()["session"]["token"]

    container = get_container()
    task = container.task_service.create_task(
        StyleTaskRequest(
            photo_url="/uploads/private-task.jpg",
            photo_object_key="private-task.jpg",
            scene=Scene.daily,
            budget=Budget(min=300, max=800),
        ),
        owner_id=first_user_id,
    )

    task_url = f"/api/v1/style-tasks/{task.task_id}"
    first_response = client.get(task_url, headers={"Authorization": f"Bearer {first_token}"})
    second_response = client.get(task_url, headers={"Authorization": f"Bearer {second_token}"})
    anonymous_response = client.get(task_url)

    assert first_response.status_code == 200
    assert first_response.json()["task_id"] == task.task_id
    assert second_response.status_code == 404
    assert anonymous_response.status_code == 404


def test_anonymous_ownerless_task_can_be_polled_by_id(tmp_path):
    client = product_client(tmp_path)
    container = get_container()
    task = container.task_service.create_task(
        StyleTaskRequest(
            photo_url="/uploads/anonymous-task.jpg",
            photo_object_key="anonymous-task.jpg",
            scene=Scene.daily,
            budget=Budget(min=300, max=800),
        ),
        owner_id=None,
    )

    response = client.get(f"/api/v1/style-tasks/{task.task_id}")

    assert response.status_code == 200
    assert response.json()["task_id"] == task.task_id


def test_private_task_result_retry_and_trace_are_scoped_to_owner(tmp_path):
    client, verifier = authenticated_product_client(tmp_path)
    first_login_response = client.post("/api/v1/auth/google", json={"id_token": "header.payload.signature"})
    assert first_login_response.status_code == 200
    first_token = first_login_response.json()["session"]["token"]
    first_user_id = first_login_response.json()["user"]["user_id"]

    verifier.profile = google_profile(sub="google-sub-2", email="second@example.com", name="Second User")
    second_login_response = client.post("/api/v1/auth/google", json={"id_token": "header.payload.signature"})
    assert second_login_response.status_code == 200
    second_token = second_login_response.json()["session"]["token"]

    container = get_container()
    task = container.task_service.create_task(
        StyleTaskRequest(
            photo_url="/uploads/private-result.jpg",
            photo_object_key="private-result.jpg",
            scene=Scene.daily,
            budget=Budget(min=300, max=800),
        ),
        owner_id=first_user_id,
    )
    container.task_service.repository.complete(
        task.task_id,
        StyleTaskResult(
            task_id=task.task_id,
            status=TaskStatus.succeeded,
            outfit=OutfitCandidate(
                candidate_id="outfit_private_endpoint",
                title="Private Endpoint Look",
                items=[],
                total_price=0,
                score=0.94,
                score_breakdown={"overall": 0.94},
                why_this_works=["private endpoint coverage"],
            ),
            try_on_image_url="/try-on/private-endpoint.jpg",
        ),
    )

    result_url = f"/api/v1/style-tasks/{task.task_id}/result"
    retry_url = f"/api/v1/style-tasks/{task.task_id}/retry-image"
    trace_url = f"/api/v1/style-tasks/{task.task_id}/trace"

    first_result_response = client.get(result_url, headers={"Authorization": f"Bearer {first_token}"})
    second_result_response = client.get(result_url, headers={"Authorization": f"Bearer {second_token}"})
    anonymous_result_response = client.get(result_url)
    second_retry_response = client.post(retry_url, headers={"Authorization": f"Bearer {second_token}"})
    anonymous_retry_response = client.post(retry_url)
    second_trace_response = client.get(trace_url, headers={"Authorization": f"Bearer {second_token}"})
    anonymous_trace_response = client.get(trace_url)

    assert first_result_response.status_code == 200
    assert first_result_response.json()["outfit"]["title"] == "Private Endpoint Look"
    assert second_result_response.status_code == 404
    assert anonymous_result_response.status_code == 404
    assert second_retry_response.status_code == 404
    assert anonymous_retry_response.status_code == 404
    assert second_trace_response.status_code == 404
    assert anonymous_trace_response.status_code == 404
