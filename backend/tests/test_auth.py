from __future__ import annotations

from app.providers.auth import AuthStore, GoogleProfile


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
