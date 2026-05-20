from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import create_app
from app.providers.auth import AuthStore, GoogleProfile
from app.providers.google_auth import GoogleIdTokenVerifier
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


def test_update_style_profile_route_recomputes_metrics(tmp_path):
    client = product_client(tmp_path)

    response = client.put(
        "/api/v1/profile/style",
        json={"height_cm": 175, "body_shape": "straight", "skin_tone": "cool", "hair_tone": "black"},
    )

    assert response.status_code == 200
    body = response.json()
    metrics = {metric["label"]: metric["value"] for metric in body["feature_metrics"]}
    assert body["height_cm"] == 175
    assert body["feature_metrics"][0]["label"] == "Height"
    assert metrics["Height"] == "175 cm"
    assert metrics["Body shape"] == "straight"
    assert metrics["Skin tone"] == "cool"
    assert metrics["Hair tone"] == "black"


def test_home_returns_seeded_recommendations_without_tasks(tmp_path):
    client = product_client(tmp_path)

    response = client.get("/api/v1/home")

    assert response.status_code == 200
    body = response.json()
    assert body["feature_summary"]["score"] >= 0.8
    assert len(body["recommendations"]) >= 3
    assert body["today_suggestion"]["title"]
    assert body["backend_status"]["ok"] is True


def test_inspirations_can_filter_by_scene(tmp_path):
    client = product_client(tmp_path)

    response = client.get("/api/v1/inspirations?scene=commute")

    assert response.status_code == 200
    body = response.json()
    assert body["items"]
    assert {item["scene"] for item in body["items"]} == {"commute"}


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


def test_home_uses_recent_completed_task(tmp_path):
    client = product_client(tmp_path)
    container = get_container()
    task = container.task_service.create_task(
        StyleTaskRequest(
            photo_url="/uploads/photo.jpg",
            photo_object_key="photo.jpg",
            scene=Scene.date,
            budget=Budget(min=300, max=800),
        )
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

    response = client.get("/api/v1/home")

    assert response.status_code == 200
    first = response.json()["recommendations"][0]
    assert first["source_task_id"] == task.task_id
    assert first["title"] == "Task Backed Look"
    assert first["scene"] == "date"


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
