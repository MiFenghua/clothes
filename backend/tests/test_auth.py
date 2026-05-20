from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.providers.auth import AuthStore, GoogleProfile
from app.providers.google_auth import GoogleIdTokenVerifier, GoogleTokenVerificationError
from app.main import create_app
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


def test_auth_me_returns_current_user_from_bearer_token(tmp_path):
    client, _ = auth_client(tmp_path)
    login = client.post("/api/v1/auth/google", json={"id_token": "fake-google-id-token-value"})
    token = login.json()["session"]["token"]

    response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert response.json()["user"]["email"] == "style.user@example.com"


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
