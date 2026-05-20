from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import create_app
from app.providers.auth import AuthStore
from app.services.container import get_container


def product_client(tmp_path) -> TestClient:
    get_container.cache_clear()
    container = get_container()
    container.settings.auth_store_path = tmp_path / "product-auth.json"
    container.auth_store = AuthStore(container.settings.auth_store_path, session_max_age_days=30)
    return TestClient(create_app())


def test_profile_returns_anonymous_default(tmp_path):
    client = product_client(tmp_path)

    response = client.get("/api/v1/profile")

    assert response.status_code == 200
    body = response.json()
    assert body["user"] is None
    assert body["style_profile"]["display_name"] == "Style User"
    assert body["style_profile"]["feature_metrics"][0]["label"] == "Height"
    assert "clean" in body["style_profile"]["style_keywords"]


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
