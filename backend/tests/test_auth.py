from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.providers import google_auth
from app.providers.auth import AuthStore, GoogleProfile
from app.providers.google_auth import (
    GoogleAuthNotConfiguredError,
    GoogleIdTokenVerifier,
    GoogleOAuthIdTokenVerifier,
    GoogleTokenVerificationError,
)
from app.services.container import get_container


def profile(**overrides: object) -> GoogleProfile:
    data = {
        "sub": "google-sub-1",
        "email": "Style.User@Example.com",
        "email_verified": True,
        "name": "Style User",
        "avatar_url": "https://example.com/avatar.png",
    }
    data.update(overrides)
    return GoogleProfile(**data)


class FakeGoogleVerifier(GoogleIdTokenVerifier):
    def __init__(self) -> None:
        self.profile = profile()
        self.error: Exception | None = None

    def verify(self, id_token: str) -> GoogleProfile:
        if self.error is not None:
            raise self.error
        return self.profile


def auth_client(tmp_path) -> tuple[TestClient, FakeGoogleVerifier]:
    get_container.cache_clear()
    container = get_container()
    container.settings.auth_store_path = tmp_path / "route-auth.json"
    container.auth_store = AuthStore(container.settings.auth_store_path, session_max_age_days=30)
    verifier = FakeGoogleVerifier()
    container.google_id_token_verifier = verifier
    client = TestClient(create_app())
    return client, verifier


def test_google_login_creates_user_and_session(tmp_path):
    store = AuthStore(tmp_path / "auth.json", session_max_age_days=30)

    user = store.upsert_google_user(profile())
    session = store.create_session(user.user_id)

    assert user.email == "style.user@example.com"
    assert user.provider == "google"
    assert session.token
    stored_user = store.get_user_by_token(session.token)
    assert stored_user is not None
    assert stored_user.user_id == user.user_id
    assert session.token not in (tmp_path / "auth.json").read_text(encoding="utf-8")


def test_google_login_reuses_existing_subject(tmp_path):
    store = AuthStore(tmp_path / "auth.json", session_max_age_days=30)

    first = store.upsert_google_user(profile(name="First Name"))
    second = store.upsert_google_user(profile(name="Updated Name"))

    assert second.user_id == first.user_id
    assert second.name == "Updated Name"


def test_google_login_links_existing_email(tmp_path):
    store = AuthStore(tmp_path / "auth.json", session_max_age_days=30)

    first = store.upsert_google_user(profile(sub="sub-a"))
    second = store.upsert_google_user(profile(sub="sub-b", email="style.user@example.com"))

    assert second.user_id == first.user_id
    assert second.google_sub == "sub-b"


def test_destroy_session_invalidates_token(tmp_path):
    store = AuthStore(tmp_path / "auth.json", session_max_age_days=30)
    user = store.upsert_google_user(profile())
    session = store.create_session(user.user_id)

    store.destroy_session(session.token)

    assert store.get_user_by_token(session.token) is None


def test_google_login_rejects_unverified_email(tmp_path):
    store = AuthStore(tmp_path / "auth.json", session_max_age_days=30)

    with pytest.raises(ValueError, match="verified"):
        store.upsert_google_user(profile(email_verified=False))

    assert not (tmp_path / "auth.json").exists()


def test_google_login_rejects_existing_subject_email_takeover(tmp_path):
    store = AuthStore(tmp_path / "auth.json", session_max_age_days=30)
    first = store.upsert_google_user(profile(sub="sub-a", email="first@example.com"))
    second = store.upsert_google_user(profile(sub="sub-b", email="second@example.com"))

    with pytest.raises(ValueError, match="email"):
        store.upsert_google_user(profile(sub="sub-a", email="SECOND@example.com"))

    data = json.loads((tmp_path / "auth.json").read_text(encoding="utf-8"))
    users_by_sub = {user["google_sub"]: user for user in data["users"]}
    assert users_by_sub["sub-a"]["user_id"] == first.user_id
    assert users_by_sub["sub-a"]["email"] == "first@example.com"
    assert users_by_sub["sub-b"]["user_id"] == second.user_id
    assert users_by_sub["sub-b"]["email"] == "second@example.com"


def test_create_session_rejects_unknown_user_id(tmp_path):
    store = AuthStore(tmp_path / "auth.json", session_max_age_days=30)

    with pytest.raises(ValueError, match="user"):
        store.create_session("missing-user")

    assert not (tmp_path / "auth.json").exists()


def test_auth_store_saves_with_atomic_replace(tmp_path, monkeypatch):
    store_path = tmp_path / "auth.json"
    store = AuthStore(store_path, session_max_age_days=30)
    original_write_text = Path.write_text

    def fail_if_direct_target_write(self: Path, *args: object, **kwargs: object) -> int:
        if self == store_path:
            raise AssertionError("auth store must not write directly to target path")
        return original_write_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "write_text", fail_if_direct_target_write)

    user = store.upsert_google_user(profile())
    session = store.create_session(user.user_id)

    reloaded = AuthStore(store_path, session_max_age_days=30)
    stored_user = reloaded.get_user_by_token(session.token)
    assert stored_user is not None
    assert stored_user.user_id == user.user_id


def test_google_oauth_verifier_requires_client_id_without_calling_google(monkeypatch):
    called = False

    def verify_oauth2_token(*args: object) -> dict:
        nonlocal called
        called = True
        return {}

    monkeypatch.setattr(google_auth.id_token, "verify_oauth2_token", verify_oauth2_token)

    with pytest.raises(GoogleAuthNotConfiguredError, match="client id"):
        GoogleOAuthIdTokenVerifier(None).verify("fake-token")

    assert called is False


def test_google_oauth_verifier_maps_google_value_error(monkeypatch):
    def verify_oauth2_token(*args: object) -> dict:
        raise ValueError("bad token")

    monkeypatch.setattr(google_auth.id_token, "verify_oauth2_token", verify_oauth2_token)

    with pytest.raises(GoogleTokenVerificationError, match="Invalid Google ID token"):
        GoogleOAuthIdTokenVerifier("client-id").verify("fake-token")


@pytest.mark.parametrize(
    "payload",
    [
        {"email": "style.user@example.com", "email_verified": True},
        {"sub": "google-sub-1", "email_verified": True},
    ],
)
def test_google_oauth_verifier_rejects_missing_subject_or_email(monkeypatch, payload):
    def verify_oauth2_token(*args: object) -> dict:
        return payload

    monkeypatch.setattr(google_auth.id_token, "verify_oauth2_token", verify_oauth2_token)

    with pytest.raises(GoogleTokenVerificationError, match="Invalid Google ID token"):
        GoogleOAuthIdTokenVerifier("client-id").verify("fake-token")


def test_google_oauth_verifier_accepts_string_true_email_verified(monkeypatch):
    def verify_oauth2_token(*args: object) -> dict:
        return {
            "sub": "google-sub-1",
            "email": "style.user@example.com",
            "email_verified": "true",
            "name": "Style User",
            "picture": "https://example.com/avatar.png",
        }

    monkeypatch.setattr(google_auth.id_token, "verify_oauth2_token", verify_oauth2_token)

    profile = GoogleOAuthIdTokenVerifier("client-id").verify("fake-token")

    assert profile.email_verified is True
    assert profile.sub == "google-sub-1"
    assert profile.email == "style.user@example.com"


def test_google_auth_route_returns_user_and_session_for_valid_profile(tmp_path):
    client, verifier = auth_client(tmp_path)
    verifier.profile = profile()

    response = client.post("/api/v1/auth/google", json={"id_token": "fake-google-id-token-value"})

    assert response.status_code == 200
    body = response.json()
    assert body["user"]["email"] == "style.user@example.com"
    assert body["user"]["provider"] == "google"
    assert body["session"]["token"]
    assert body["session"]["expires_at"]


def test_google_auth_route_rejects_unverified_email(tmp_path):
    client, verifier = auth_client(tmp_path)
    verifier.profile = profile(email_verified=False)

    response = client.post("/api/v1/auth/google", json={"id_token": "fake-google-id-token-value"})

    assert response.status_code == 401
    assert response.json() == {"detail": "Google email is not verified"}


def test_google_auth_route_rejects_invalid_google_token(tmp_path):
    client, verifier = auth_client(tmp_path)
    verifier.error = GoogleTokenVerificationError("Invalid Google ID token")

    response = client.post("/api/v1/auth/google", json={"id_token": "fake-google-id-token-value"})

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid Google ID token"}


def test_google_auth_route_returns_conflict_for_email_takeover(tmp_path):
    client, verifier = auth_client(tmp_path)

    verifier.profile = profile(sub="sub-a", email="first@example.com")
    assert client.post("/api/v1/auth/google", json={"id_token": "fake-google-id-token-value"}).status_code == 200
    verifier.profile = profile(sub="sub-b", email="second@example.com")
    assert client.post("/api/v1/auth/google", json={"id_token": "fake-google-id-token-value"}).status_code == 200

    verifier.profile = profile(sub="sub-a", email="second@example.com")
    response = client.post("/api/v1/auth/google", json={"id_token": "fake-google-id-token-value"})

    assert response.status_code == 409
    assert response.json() == {"detail": "Google profile email belongs to another user"}


def test_auth_me_returns_current_user_from_bearer_token(tmp_path):
    client, _ = auth_client(tmp_path)
    login = client.post("/api/v1/auth/google", json={"id_token": "fake-google-id-token-value"})
    token = login.json()["session"]["token"]

    response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert response.json()["user"]["email"] == "style.user@example.com"


@pytest.mark.parametrize("authorization", [None, "", "Basic abc", "Bearer"])
def test_auth_me_returns_no_user_for_missing_or_malformed_authorization(tmp_path, authorization):
    client, _ = auth_client(tmp_path)
    headers = {"Authorization": authorization} if authorization is not None else {}

    response = client.get("/api/v1/auth/me", headers=headers)

    assert response.status_code == 200
    assert response.json() == {"user": None}


def test_logout_invalidates_bearer_session(tmp_path):
    client, _ = auth_client(tmp_path)
    login = client.post("/api/v1/auth/google", json={"id_token": "fake-google-id-token-value"})
    token = login.json()["session"]["token"]

    response = client.post("/api/v1/auth/logout", headers={"Authorization": f"Bearer {token}"})
    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert response.json() == {"ok": True}
    assert me.status_code == 200
    assert me.json() == {"user": None}


def test_logout_without_token_is_idempotent(tmp_path):
    client, _ = auth_client(tmp_path)

    response = client.post("/api/v1/auth/logout")

    assert response.status_code == 200
    assert response.json() == {"ok": True}


def test_wardrobe_items_are_scoped_to_current_user(tmp_path):
    client, verifier = auth_client(tmp_path)
    first_login_response = client.post("/api/v1/auth/google", json={"id_token": "header.payload.signature"})
    assert first_login_response.status_code == 200
    first_login = first_login_response.json()
    first_token = first_login["session"]["token"]

    verifier.profile = profile(sub="google-sub-2", email="second@example.com", name="Second User")
    second_login_response = client.post("/api/v1/auth/google", json={"id_token": "header.payload.signature"})
    assert second_login_response.status_code == 200
    second_login = second_login_response.json()
    second_token = second_login["session"]["token"]

    files = {"photo": ("shirt.jpg", b"fake image", "image/jpeg")}
    data = {"category": "top", "title": "White shirt"}
    create_response = client.post(
        "/api/v1/wardrobe-items",
        data=data,
        files=files,
        headers={"Authorization": f"Bearer {first_token}"},
    )
    assert create_response.status_code == 201

    first_items_response = client.get("/api/v1/wardrobe-items", headers={"Authorization": f"Bearer {first_token}"})
    second_items_response = client.get("/api/v1/wardrobe-items", headers={"Authorization": f"Bearer {second_token}"})
    assert first_items_response.status_code == 200
    assert second_items_response.status_code == 200
    first_items = first_items_response.json()
    second_items = second_items_response.json()

    assert [item["title"] for item in first_items] == ["White shirt"]
    assert second_items == []


def test_anonymous_wardrobe_items_only_include_anonymous_items(tmp_path):
    client, _ = auth_client(tmp_path)
    login_response = client.post("/api/v1/auth/google", json={"id_token": "header.payload.signature"})
    assert login_response.status_code == 200
    token = login_response.json()["session"]["token"]

    create_user_item_response = client.post(
        "/api/v1/wardrobe-items",
        data={"category": "top", "title": "White shirt"},
        files={"photo": ("shirt.jpg", b"fake image", "image/jpeg")},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert create_user_item_response.status_code == 201

    anonymous_items_response = client.get("/api/v1/wardrobe-items")
    assert anonymous_items_response.status_code == 200
    anonymous_titles = [item["title"] for item in anonymous_items_response.json()]
    assert "White shirt" not in anonymous_titles

    create_anonymous_item_response = client.post(
        "/api/v1/wardrobe-items",
        data={"category": "accessory", "title": "Black hat"},
        files={"photo": ("hat.jpg", b"fake image", "image/jpeg")},
    )
    assert create_anonymous_item_response.status_code == 201

    anonymous_items_response = client.get("/api/v1/wardrobe-items")
    assert anonymous_items_response.status_code == 200
    anonymous_titles = [item["title"] for item in anonymous_items_response.json()]
    assert "White shirt" not in anonymous_titles
    assert "Black hat" in anonymous_titles
