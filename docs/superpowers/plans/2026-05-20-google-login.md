# Google Login Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add real Google third-party login to the Android app and Python FastAPI backend.

**Architecture:** Android uses Credential Manager to get a Google ID token, exchanges it with the Python backend, stores the backend session in `SharedPreferences`, and sends `Authorization: Bearer <token>` on later backend requests. The backend verifies the Google ID token through an injectable verifier, upserts users in a JSON auth store, hashes session tokens at rest, and exposes `/api/v1/auth/google`, `/api/v1/auth/me`, and `/api/v1/auth/logout`.

**Tech Stack:** Kotlin Compose, AndroidX Credential Manager, Google Identity `googleid`, FastAPI, Pydantic, pytest, JSON file storage.

---

## File Structure

- Create `backend/app/schemas/auth.py`: Pydantic request/response models for public users and sessions.
- Create `backend/app/providers/auth.py`: JSON-backed user/session store, token hashing, session lookup, and Google user upsert.
- Create `backend/app/providers/google_auth.py`: Google ID token verifier protocol plus production verifier and test fake support.
- Create `backend/tests/test_auth.py`: FastAPI auth route tests using a fake verifier and temporary auth store.
- Modify `backend/app/config.py`: add Google client id, auth store path, and session lifetime settings.
- Modify `backend/app/services/container.py`: construct `AuthStore` and Google verifier.
- Modify `backend/app/api/routes.py`: add auth endpoints and current-user dependency for wardrobe ownership.
- Modify `backend/pyproject.toml`: add `google-auth` for production ID token verification.
- Create `android/app/src/main/kotlin/com/clothes/app/AuthModels.kt`: Android auth DTOs and login result models.
- Create `android/app/src/main/kotlin/com/clothes/app/AuthSessionStore.kt`: `SharedPreferences` session persistence.
- Create `android/app/src/main/kotlin/com/clothes/app/GoogleAuthClient.kt`: Credential Manager wrapper.
- Modify `android/app/src/main/kotlin/com/clothes/app/StyleApi.kt`: auth API calls, JSON parsers, and bearer-token header support.
- Modify `android/app/src/main/kotlin/com/clothes/app/StyleModels.kt`: add auth state fields.
- Modify `android/app/src/main/kotlin/com/clothes/app/StyleViewModel.kt`: initialize session, perform Google sign-in exchange, logout, and attach auth token to API.
- Modify `android/app/src/main/kotlin/com/clothes/app/MainActivity.kt`: create `GoogleAuthClient` and pass it into login flow.
- Modify `android/app/src/main/kotlin/com/clothes/app/ui/screens/OnboardingScreens.kt`: replace mock phone/WeChat login controls with Google login UI.
- Modify `android/app/src/main/res/values/strings.xml`: add `google_web_client_id`.
- Modify `android/app/build.gradle`: add Credential Manager and Google ID dependencies.
- Modify `README.md`: document Google OAuth setup for Android and backend.

---

### Task 1: Backend Auth Models And Store

**Files:**
- Create: `backend/app/schemas/auth.py`
- Create: `backend/app/providers/auth.py`
- Modify: `backend/app/config.py`
- Test: `backend/tests/test_auth.py`

- [ ] **Step 1: Write failing auth-store tests**

Create `backend/tests/test_auth.py` with these tests first:

```python
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
```

- [ ] **Step 2: Run the backend auth-store test to verify it fails**

Run:

```bash
cd backend
python -m pytest tests/test_auth.py -q
```

Expected: FAIL with `ModuleNotFoundError: No module named 'app.providers.auth'`.

- [ ] **Step 3: Add auth schemas**

Create `backend/app/schemas/auth.py`:

```python
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


AuthProvider = Literal["google"]


class PublicUser(BaseModel):
    user_id: str
    email: str
    name: str
    avatar_url: str | None = None
    provider: AuthProvider = "google"


class AuthSession(BaseModel):
    token: str
    expires_at: datetime


class AuthUserRecord(PublicUser):
    google_sub: str
    created_at: datetime
    updated_at: datetime


class AuthSessionRecord(BaseModel):
    session_id: str
    user_id: str
    token_hash: str
    created_at: datetime
    expires_at: datetime


class GoogleLoginRequest(BaseModel):
    id_token: str = Field(min_length=20)


class AuthResponse(BaseModel):
    user: PublicUser
    session: AuthSession
```

- [ ] **Step 4: Add JSON auth store**

Create `backend/app/providers/auth.py`:

```python
from __future__ import annotations

import hashlib
import json
import secrets
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

from pydantic import BaseModel

from app.schemas.auth import AuthSession, AuthSessionRecord, AuthUserRecord, PublicUser


class GoogleProfile(BaseModel):
    sub: str
    email: str
    email_verified: bool
    name: str | None = None
    avatar_url: str | None = None


class AuthStore:
    def __init__(self, store_path: Path, session_max_age_days: int) -> None:
        self.store_path = store_path
        self.session_max_age_days = session_max_age_days
        self.users: list[AuthUserRecord] = []
        self.sessions: list[AuthSessionRecord] = []
        self._load()
        self._prune_expired_sessions()

    def upsert_google_user(self, profile: GoogleProfile) -> AuthUserRecord:
        email = profile.email.strip().lower()
        now = self._now()
        user = self._find_user_by_google_sub(profile.sub) or self._find_user_by_email(email)
        if user is not None:
            updated = user.model_copy(
                update={
                    "google_sub": profile.sub,
                    "email": email,
                    "name": profile.name or user.name,
                    "avatar_url": profile.avatar_url or user.avatar_url,
                    "updated_at": now,
                }
            )
            self.users = [updated if candidate.user_id == user.user_id else candidate for candidate in self.users]
            self._save()
            return updated

        created = AuthUserRecord(
            user_id=f"user_{uuid4().hex[:16]}",
            google_sub=profile.sub,
            email=email,
            name=profile.name or email.split("@")[0] or "Google User",
            avatar_url=profile.avatar_url,
            provider="google",
            created_at=now,
            updated_at=now,
        )
        self.users.append(created)
        self._save()
        return created

    def create_session(self, user_id: str) -> AuthSession:
        self._prune_expired_sessions()
        now = self._now()
        expires_at = now + timedelta(days=self.session_max_age_days)
        token = secrets.token_urlsafe(32)
        self.sessions.append(
            AuthSessionRecord(
                session_id=f"session_{uuid4().hex[:16]}",
                user_id=user_id,
                token_hash=self._hash_token(token),
                created_at=now,
                expires_at=expires_at,
            )
        )
        self._save()
        return AuthSession(token=token, expires_at=expires_at)

    def get_user_by_token(self, token: str | None) -> PublicUser | None:
        if not token:
            return None
        self._prune_expired_sessions()
        token_hash = self._hash_token(token)
        session = next((candidate for candidate in self.sessions if candidate.token_hash == token_hash), None)
        if session is None:
            return None
        user = next((candidate for candidate in self.users if candidate.user_id == session.user_id), None)
        return self._public_user(user) if user else None

    def destroy_session(self, token: str | None) -> None:
        if not token:
            return
        token_hash = self._hash_token(token)
        next_sessions = [session for session in self.sessions if session.token_hash != token_hash]
        if len(next_sessions) == len(self.sessions):
            return
        self.sessions = next_sessions
        self._save()

    def _find_user_by_google_sub(self, google_sub: str) -> AuthUserRecord | None:
        return next((user for user in self.users if user.google_sub == google_sub), None)

    def _find_user_by_email(self, email: str) -> AuthUserRecord | None:
        return next((user for user in self.users if user.email == email), None)

    def _load(self) -> None:
        if not self.store_path.exists():
            return
        data = json.loads(self.store_path.read_text(encoding="utf-8"))
        self.users = [AuthUserRecord.model_validate(item) for item in data.get("users", [])]
        self.sessions = [AuthSessionRecord.model_validate(item) for item in data.get("sessions", [])]

    def _save(self) -> None:
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "users": [user.model_dump(mode="json") for user in self.users],
            "sessions": [session.model_dump(mode="json") for session in self.sessions],
        }
        self.store_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def _prune_expired_sessions(self) -> None:
        now = self._now()
        next_sessions = [session for session in self.sessions if session.expires_at > now]
        if len(next_sessions) == len(self.sessions):
            return
        self.sessions = next_sessions
        self._save()

    @staticmethod
    def _hash_token(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    @staticmethod
    def _now() -> datetime:
        return datetime.now(UTC)

    @staticmethod
    def _public_user(user: AuthUserRecord | None) -> PublicUser | None:
        if user is None:
            return None
        return PublicUser(
            user_id=user.user_id,
            email=user.email,
            name=user.name,
            avatar_url=user.avatar_url,
            provider=user.provider,
        )
```

- [ ] **Step 5: Add backend auth settings**

Modify `backend/app/config.py` inside `Settings`:

```python
    google_client_id: str | None = None
    auth_store_path: Path = BACKEND_ROOT / "storage/auth-store.json"
    auth_session_max_age_days: int = 30
```

- [ ] **Step 6: Run auth-store tests**

Run:

```bash
cd backend
python -m pytest tests/test_auth.py -q
```

Expected: PASS for the four auth-store tests.

- [ ] **Step 7: Commit backend auth store**

Run:

```bash
git add backend/app/schemas/auth.py backend/app/providers/auth.py backend/app/config.py backend/tests/test_auth.py
git commit -m "feat: add backend auth store"
```

---

### Task 2: Backend Google Verification And Auth Routes

**Files:**
- Create: `backend/app/providers/google_auth.py`
- Modify: `backend/app/services/container.py`
- Modify: `backend/app/api/routes.py`
- Modify: `backend/pyproject.toml`
- Test: `backend/tests/test_auth.py`

- [ ] **Step 1: Extend tests for auth endpoints**

Append to `backend/tests/test_auth.py`:

```python
from fastapi.testclient import TestClient

from app.api import routes
from app.main import create_app
from app.providers.google_auth import GoogleIdTokenVerifier, GoogleTokenVerificationError
from app.services.container import get_container


class FakeGoogleVerifier(GoogleIdTokenVerifier):
    def __init__(self) -> None:
        self.profile = profile()
        self.error: Exception | None = None

    def verify(self, id_token: str) -> GoogleProfile:
        if self.error is not None:
            raise self.error
        return self.profile


def auth_client(tmp_path):
    get_container.cache_clear()
    container = get_container()
    container.settings.auth_store_path = tmp_path / "route-auth.json"
    container.auth_store = AuthStore(container.settings.auth_store_path, session_max_age_days=30)
    verifier = FakeGoogleVerifier()
    container.google_id_token_verifier = verifier
    client = TestClient(create_app())
    return client, verifier


def test_google_login_route_returns_user_and_session(tmp_path):
    client, _verifier = auth_client(tmp_path)

    response = client.post("/api/v1/auth/google", json={"id_token": "header.payload.signature"})

    assert response.status_code == 200
    body = response.json()
    assert body["user"]["email"] == "style.user@example.com"
    assert body["session"]["token"]
    assert body["session"]["expires_at"]


def test_google_login_route_rejects_unverified_email(tmp_path):
    client, verifier = auth_client(tmp_path)
    verifier.profile = profile(email_verified=False)

    response = client.post("/api/v1/auth/google", json={"id_token": "header.payload.signature"})

    assert response.status_code == 401
    assert response.json()["detail"] == "Google email is not verified"


def test_google_login_route_rejects_invalid_google_token(tmp_path):
    client, verifier = auth_client(tmp_path)
    verifier.error = GoogleTokenVerificationError("Invalid Google ID token")

    response = client.post("/api/v1/auth/google", json={"id_token": "header.payload.signature"})

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid Google ID token"


def test_me_and_logout_use_bearer_session(tmp_path):
    client, _verifier = auth_client(tmp_path)
    login = client.post("/api/v1/auth/google", json={"id_token": "header.payload.signature"}).json()
    token = login["session"]["token"]

    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["user"]["email"] == "style.user@example.com"

    logout = client.post("/api/v1/auth/logout", headers={"Authorization": f"Bearer {token}"})
    assert logout.status_code == 200
    assert logout.json() == {"ok": True}

    after = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert after.status_code == 200
    assert after.json() == {"user": None}
```

- [ ] **Step 2: Run endpoint tests to verify they fail**

Run:

```bash
cd backend
python -m pytest tests/test_auth.py -q
```

Expected: FAIL with `ModuleNotFoundError: No module named 'app.providers.google_auth'` or missing auth route assertions.

- [ ] **Step 3: Add production Google token verifier**

Create `backend/app/providers/google_auth.py`:

```python
from __future__ import annotations

from typing import Protocol

from google.auth.transport import requests
from google.oauth2 import id_token

from app.providers.auth import GoogleProfile


class GoogleTokenVerificationError(Exception):
    pass


class GoogleAuthNotConfiguredError(Exception):
    pass


class GoogleIdTokenVerifier(Protocol):
    def verify(self, id_token_value: str) -> GoogleProfile:
        ...


class GoogleOAuthIdTokenVerifier:
    def __init__(self, client_id: str | None) -> None:
        self.client_id = client_id

    def verify(self, id_token_value: str) -> GoogleProfile:
        if not self.client_id:
            raise GoogleAuthNotConfiguredError("Google client id is not configured")
        try:
            payload = id_token.verify_oauth2_token(id_token_value, requests.Request(), self.client_id)
        except ValueError as exc:
            raise GoogleTokenVerificationError("Invalid Google ID token") from exc

        subject = str(payload.get("sub") or "")
        email = str(payload.get("email") or "")
        if not subject or not email:
            raise GoogleTokenVerificationError("Invalid Google ID token")
        return GoogleProfile(
            sub=subject,
            email=email,
            email_verified=payload.get("email_verified") is True or str(payload.get("email_verified")).lower() == "true",
            name=str(payload.get("name") or "") or None,
            avatar_url=str(payload.get("picture") or "") or None,
        )
```

- [ ] **Step 4: Add `google-auth` dependency**

Modify `backend/pyproject.toml` dependencies:

```toml
  "google-auth>=2.35.0",
```

Place it with the other backend dependencies.

- [ ] **Step 5: Wire auth services into container**

Modify imports in `backend/app/services/container.py`:

```python
from app.providers.auth import AuthStore
from app.providers.google_auth import GoogleOAuthIdTokenVerifier
```

Add these fields in `AppContainer.__init__` after `self.storage`:

```python
        self.auth_store = AuthStore(
            self.settings.auth_store_path,
            session_max_age_days=self.settings.auth_session_max_age_days,
        )
        self.google_id_token_verifier = GoogleOAuthIdTokenVerifier(self.settings.google_client_id)
```

- [ ] **Step 6: Add route helpers and auth endpoints**

Modify imports in `backend/app/api/routes.py`:

```python
from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, Header, HTTPException, UploadFile

from app.providers.google_auth import GoogleAuthNotConfiguredError, GoogleTokenVerificationError
from app.schemas.auth import AuthResponse, GoogleLoginRequest, PublicUser
```

Add these helpers after `container_dependency`:

```python
def bearer_token(authorization: str | None) -> str | None:
    if not authorization:
        return None
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        return None
    return token.strip()


def current_user(
    container: Annotated[AppContainer, Depends(container_dependency)],
    authorization: Annotated[str | None, Header()] = None,
) -> PublicUser | None:
    return container.auth_store.get_user_by_token(bearer_token(authorization))
```

Add these routes after `health`:

```python
@router.post("/api/v1/auth/google", response_model=AuthResponse)
async def login_with_google(
    payload: GoogleLoginRequest,
    container: Annotated[AppContainer, Depends(container_dependency)],
) -> AuthResponse:
    try:
        profile = container.google_id_token_verifier.verify(payload.id_token)
    except GoogleAuthNotConfiguredError as exc:
        raise HTTPException(status_code=503, detail="Google login is not configured") from exc
    except GoogleTokenVerificationError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc

    if not profile.email_verified:
        raise HTTPException(status_code=401, detail="Google email is not verified")

    user = container.auth_store.upsert_google_user(profile)
    session = container.auth_store.create_session(user.user_id)
    return AuthResponse(user=user, session=session)


@router.get("/api/v1/auth/me")
async def get_current_auth_user(user: Annotated[PublicUser | None, Depends(current_user)]) -> dict[str, PublicUser | None]:
    return {"user": user}


@router.post("/api/v1/auth/logout")
async def logout(
    container: Annotated[AppContainer, Depends(container_dependency)],
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, bool]:
    container.auth_store.destroy_session(bearer_token(authorization))
    return {"ok": True}
```

- [ ] **Step 7: Run endpoint tests**

Run:

```bash
cd backend
python -m pytest tests/test_auth.py -q
```

Expected: PASS.

- [ ] **Step 8: Run full backend tests**

Run:

```bash
cd backend
python -m pytest -q
```

Expected: PASS.

- [ ] **Step 9: Commit backend auth routes**

Run:

```bash
git add backend/app/providers/google_auth.py backend/app/services/container.py backend/app/api/routes.py backend/pyproject.toml backend/tests/test_auth.py
git commit -m "feat: add google auth endpoints"
```

---

### Task 3: Backend Auth Context For Wardrobe Ownership

**Files:**
- Modify: `backend/app/api/routes.py`
- Test: `backend/tests/test_auth.py`

- [ ] **Step 1: Add wardrobe owner test**

Append to `backend/tests/test_auth.py`:

```python
def test_wardrobe_items_are_scoped_to_current_user(tmp_path):
    client, verifier = auth_client(tmp_path)
    first_login = client.post("/api/v1/auth/google", json={"id_token": "header.payload.signature"}).json()
    first_token = first_login["session"]["token"]

    verifier.profile = profile(sub="google-sub-2", email="second@example.com", name="Second User")
    second_login = client.post("/api/v1/auth/google", json={"id_token": "header.payload.signature"}).json()
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

    first_items = client.get("/api/v1/wardrobe-items", headers={"Authorization": f"Bearer {first_token}"}).json()
    second_items = client.get("/api/v1/wardrobe-items", headers={"Authorization": f"Bearer {second_token}"}).json()

    assert [item["title"] for item in first_items] == ["White shirt"]
    assert second_items == []
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```bash
cd backend
python -m pytest tests/test_auth.py::test_wardrobe_items_are_scoped_to_current_user -q
```

Expected: FAIL because wardrobe items are not assigned to the current user.

- [ ] **Step 3: Pass current user into wardrobe routes**

Modify `list_wardrobe_items` in `backend/app/api/routes.py`:

```python
@router.get("/api/v1/wardrobe-items", response_model=list[WardrobeItem])
async def list_wardrobe_items(
    container: Annotated[AppContainer, Depends(container_dependency)],
    user: Annotated[PublicUser | None, Depends(current_user)],
) -> list[WardrobeItem]:
    return container.task_service.list_wardrobe_items(user.user_id if user else None)
```

Modify `create_wardrobe_item` signature to include:

```python
    user: Annotated[PublicUser | None, Depends(current_user)],
```

Modify the `WardrobeItem` construction:

```python
        owner_id=user.user_id if user else None,
```

- [ ] **Step 4: Run the wardrobe owner test**

Run:

```bash
cd backend
python -m pytest tests/test_auth.py::test_wardrobe_items_are_scoped_to_current_user -q
```

Expected: PASS.

- [ ] **Step 5: Run backend tests**

Run:

```bash
cd backend
python -m pytest -q
```

Expected: PASS.

- [ ] **Step 6: Commit wardrobe auth context**

Run:

```bash
git add backend/app/api/routes.py backend/tests/test_auth.py
git commit -m "feat: scope wardrobe items by auth user"
```

---

### Task 4: Android Auth Models, Store, And API

**Files:**
- Create: `android/app/src/main/kotlin/com/clothes/app/AuthModels.kt`
- Create: `android/app/src/main/kotlin/com/clothes/app/AuthSessionStore.kt`
- Modify: `android/app/src/main/kotlin/com/clothes/app/StyleApi.kt`
- Modify: `android/app/src/main/kotlin/com/clothes/app/StyleModels.kt`

- [ ] **Step 1: Add Android auth DTOs**

Create `android/app/src/main/kotlin/com/clothes/app/AuthModels.kt`:

```kotlin
package com.clothes.app

data class PublicUser(
    val userId: String,
    val email: String,
    val name: String,
    val avatarUrl: String?,
    val provider: String,
)

data class AuthSession(
    val token: String,
    val expiresAt: String,
)

data class AuthResponse(
    val user: PublicUser,
    val session: AuthSession,
)

sealed interface GoogleSignInResult {
    data class Success(val idToken: String) : GoogleSignInResult
    data object Cancelled : GoogleSignInResult
    data class Failure(val message: String) : GoogleSignInResult
}
```

- [ ] **Step 2: Add SharedPreferences auth session store**

Create `android/app/src/main/kotlin/com/clothes/app/AuthSessionStore.kt`:

```kotlin
package com.clothes.app

import android.content.Context
import org.json.JSONObject

class AuthSessionStore(context: Context) {
    private val preferences = context.getSharedPreferences("cloz_auth", Context.MODE_PRIVATE)

    fun save(auth: AuthResponse) {
        preferences.edit()
            .putString(KEY_TOKEN, auth.session.token)
            .putString(KEY_EXPIRES_AT, auth.session.expiresAt)
            .putString(KEY_USER, JSONObject().apply {
                put("user_id", auth.user.userId)
                put("email", auth.user.email)
                put("name", auth.user.name)
                put("avatar_url", auth.user.avatarUrl)
                put("provider", auth.user.provider)
            }.toString())
            .apply()
    }

    fun token(): String? = preferences.getString(KEY_TOKEN, null)?.takeIf { it.isNotBlank() }

    fun user(): PublicUser? {
        val raw = preferences.getString(KEY_USER, null) ?: return null
        return runCatching { parsePublicUser(JSONObject(raw)) }.getOrNull()
    }

    fun clear() {
        preferences.edit().clear().apply()
    }

    private companion object {
        const val KEY_TOKEN = "token"
        const val KEY_EXPIRES_AT = "expires_at"
        const val KEY_USER = "user"
    }
}
```

- [ ] **Step 3: Add auth state to UiState**

Modify `android/app/src/main/kotlin/com/clothes/app/StyleModels.kt` inside `UiState`:

```kotlin
    val currentUser: PublicUser? = null,
    val isSigningIn: Boolean = false,
```

- [ ] **Step 4: Add bearer token support to StyleApi**

Modify `StyleApi` constructor:

```kotlin
class StyleApi(
    private val context: Context,
    private val baseUrl: String,
    private val authSessionStore: AuthSessionStore? = null,
) {
```

Modify `openConnection`:

```kotlin
    private fun openConnection(path: String, method: String): HttpURLConnection {
        return (URL(baseUrl.trimEnd('/') + path).openConnection() as HttpURLConnection).apply {
            requestMethod = method
            connectTimeout = 20000
            readTimeout = 120000
            setRequestProperty("Accept", "application/json")
            authSessionStore?.token()?.let { token ->
                setRequestProperty("Authorization", "Bearer $token")
            }
        }
    }
```

- [ ] **Step 5: Add auth API methods and parsers**

Add these methods to `StyleApi` before `health()`:

```kotlin
    suspend fun loginWithGoogle(idToken: String): AuthResponse = withContext(Dispatchers.IO) {
        val connection = openConnection("/api/v1/auth/google", "POST").apply {
            doOutput = true
            setRequestProperty("Content-Type", "application/json")
        }
        try {
            val body = JSONObject().put("id_token", idToken).toString().toByteArray(Charsets.UTF_8)
            connection.outputStream.use { it.write(body) }
            parseAuthResponse(JSONObject(readResponse(connection)))
        } finally {
            connection.disconnect()
        }
    }

    suspend fun currentUser(): PublicUser? = withContext(Dispatchers.IO) {
        val connection = openConnection("/api/v1/auth/me", "GET")
        try {
            JSONObject(readResponse(connection)).optJSONObject("user")?.let(::parsePublicUser)
        } finally {
            connection.disconnect()
        }
    }

    suspend fun logout() = withContext(Dispatchers.IO) {
        val connection = openConnection("/api/v1/auth/logout", "POST").apply {
            doOutput = true
            setRequestProperty("Content-Length", "0")
        }
        try {
            readResponse(connection)
        } finally {
            connection.disconnect()
        }
    }
```

Add parser functions near the other top-level parsers:

```kotlin
fun parseAuthResponse(json: JSONObject): AuthResponse {
    return AuthResponse(
        user = parsePublicUser(json.getJSONObject("user")),
        session = parseAuthSession(json.getJSONObject("session")),
    )
}

fun parseAuthSession(json: JSONObject): AuthSession {
    return AuthSession(
        token = json.optString("token"),
        expiresAt = json.optString("expires_at"),
    )
}

fun parsePublicUser(json: JSONObject): PublicUser {
    return PublicUser(
        userId = json.optString("user_id"),
        email = json.optString("email"),
        name = json.optString("name"),
        avatarUrl = json.optNullableString("avatar_url"),
        provider = json.optString("provider"),
    )
}
```

- [ ] **Step 6: Compile Android**

Run:

```bash
cd android
.\gradlew.bat :app:compileDebugKotlin
```

Expected: BUILD SUCCESSFUL.

- [ ] **Step 7: Commit Android auth API foundation**

Run:

```bash
git add android/app/src/main/kotlin/com/clothes/app/AuthModels.kt android/app/src/main/kotlin/com/clothes/app/AuthSessionStore.kt android/app/src/main/kotlin/com/clothes/app/StyleApi.kt android/app/src/main/kotlin/com/clothes/app/StyleModels.kt
git commit -m "feat: add android auth session api"
```

---

### Task 5: Android Credential Manager Sign-In

**Files:**
- Create: `android/app/src/main/kotlin/com/clothes/app/GoogleAuthClient.kt`
- Modify: `android/app/build.gradle`
- Modify: `android/app/src/main/res/values/strings.xml`
- Modify: `android/app/src/main/kotlin/com/clothes/app/MainActivity.kt`
- Modify: `android/app/src/main/kotlin/com/clothes/app/StyleViewModel.kt`

- [ ] **Step 1: Add Credential Manager dependencies**

Modify `android/app/build.gradle` dependencies:

```gradle
    implementation "androidx.credentials:credentials:1.5.0"
    implementation "androidx.credentials:credentials-play-services-auth:1.5.0"
    implementation "com.google.android.libraries.identity.googleid:googleid:1.1.1"
```

- [ ] **Step 2: Add Google web client id resource**

Modify `android/app/src/main/res/values/strings.xml`:

```xml
<resources>
    <string name="app_name">clozAi</string>
    <string name="api_base_url">http://10.0.2.2:8000</string>
    <string name="google_web_client_id">replace-with-google-web-client-id.apps.googleusercontent.com</string>
</resources>
```

- [ ] **Step 3: Create Credential Manager wrapper**

Create `android/app/src/main/kotlin/com/clothes/app/GoogleAuthClient.kt`:

```kotlin
package com.clothes.app

import android.content.Context
import androidx.credentials.CredentialManager
import androidx.credentials.GetCredentialRequest
import androidx.credentials.exceptions.GetCredentialCancellationException
import androidx.credentials.exceptions.GetCredentialException
import com.google.android.libraries.identity.googleid.GetGoogleIdOption
import com.google.android.libraries.identity.googleid.GoogleIdTokenCredential

class GoogleAuthClient(private val context: Context) {
    private val credentialManager = CredentialManager.create(context)

    suspend fun signIn(): GoogleSignInResult {
        val clientId = context.getString(R.string.google_web_client_id)
        if (clientId.startsWith("replace-with-")) {
            return GoogleSignInResult.Failure("请先配置 Google Web Client ID")
        }
        val googleIdOption = GetGoogleIdOption.Builder()
            .setFilterByAuthorizedAccounts(false)
            .setServerClientId(clientId)
            .setAutoSelectEnabled(false)
            .build()
        val request = GetCredentialRequest.Builder()
            .addCredentialOption(googleIdOption)
            .build()
        return try {
            val result = credentialManager.getCredential(context, request)
            val credential = GoogleIdTokenCredential.createFrom(result.credential.data)
            GoogleSignInResult.Success(credential.idToken)
        } catch (_: GetCredentialCancellationException) {
            GoogleSignInResult.Cancelled
        } catch (error: GetCredentialException) {
            GoogleSignInResult.Failure(error.message ?: "Google 登录失败")
        } catch (error: Exception) {
            GoogleSignInResult.Failure(error.message ?: "Google 登录失败")
        }
    }
}
```

- [ ] **Step 4: Initialize session store and API in ViewModel**

Modify `StyleViewModel` fields:

```kotlin
    private val authSessionStore = AuthSessionStore(application)
    private val api = StyleApi(application, application.getString(R.string.api_base_url), authSessionStore)
```

Modify `init`:

```kotlin
    init {
        _uiState.update { it.copy(currentUser = authSessionStore.user()) }
        refreshCurrentUser()
        refreshBackendStatus()
    }
```

Add these methods:

```kotlin
    fun signInWithGoogle(googleAuthClient: GoogleAuthClient) {
        if (_uiState.value.isSigningIn) return
        viewModelScope.launch {
            _uiState.update { it.copy(isSigningIn = true, notice = null) }
            when (val googleResult = googleAuthClient.signIn()) {
                GoogleSignInResult.Cancelled -> {
                    _uiState.update { it.copy(isSigningIn = false, notice = "已取消 Google 登录") }
                }
                is GoogleSignInResult.Failure -> {
                    _uiState.update { it.copy(isSigningIn = false, notice = googleResult.message) }
                }
                is GoogleSignInResult.Success -> {
                    try {
                        val auth = api.loginWithGoogle(googleResult.idToken)
                        authSessionStore.save(auth)
                        _uiState.update {
                            it.copy(
                                isSigningIn = false,
                                currentUser = auth.user,
                                route = AppRoute.StyleGoal,
                                previousRoute = AppRoute.Login,
                                notice = null,
                            )
                        }
                    } catch (error: Exception) {
                        _uiState.update {
                            it.copy(
                                isSigningIn = false,
                                notice = error.message ?: "Google 登录失败",
                            )
                        }
                    }
                }
            }
        }
    }

    fun logout() {
        viewModelScope.launch {
            runCatching { api.logout() }
            authSessionStore.clear()
            _uiState.update {
                UiState(route = AppRoute.Login, previousRoute = AppRoute.Splash, backendOnline = it.backendOnline)
            }
        }
    }

    private fun refreshCurrentUser() {
        if (authSessionStore.token() == null) return
        viewModelScope.launch {
            val user = runCatching { api.currentUser() }.getOrNull()
            if (user == null) {
                authSessionStore.clear()
            }
            _uiState.update { it.copy(currentUser = user) }
        }
    }
```

- [ ] **Step 5: Pass GoogleAuthClient through MainActivity**

Modify `MainActivity.onCreate`:

```kotlin
                val googleAuthClient = remember { GoogleAuthClient(this@MainActivity) }
                ClozAiApp(viewModel, googleAuthClient)
```

Modify `ClozAiApp` signature:

```kotlin
fun ClozAiApp(viewModel: StyleViewModel, googleAuthClient: GoogleAuthClient) {
```

Modify login screen dispatch:

```kotlin
            AppRoute.Login -> LoginScreen(state, viewModel, googleAuthClient, modifier)
```

- [ ] **Step 6: Compile Android**

Run:

```bash
cd android
.\gradlew.bat :app:compileDebugKotlin
```

Expected: BUILD SUCCESSFUL.

- [ ] **Step 7: Commit Credential Manager integration**

Run:

```bash
git add android/app/build.gradle android/app/src/main/res/values/strings.xml android/app/src/main/kotlin/com/clothes/app/GoogleAuthClient.kt android/app/src/main/kotlin/com/clothes/app/MainActivity.kt android/app/src/main/kotlin/com/clothes/app/StyleViewModel.kt
git commit -m "feat: connect android google sign in"
```

---

### Task 6: Android Login UI And Logout Entry

**Files:**
- Modify: `android/app/src/main/kotlin/com/clothes/app/ui/screens/OnboardingScreens.kt`
- Modify: `android/app/src/main/kotlin/com/clothes/app/ui/screens/TabScreens.kt`

- [ ] **Step 1: Replace login screen controls**

Modify `LoginScreen` signature in `OnboardingScreens.kt`:

```kotlin
fun LoginScreen(
    state: UiState,
    viewModel: StyleViewModel,
    googleAuthClient: GoogleAuthClient,
    modifier: Modifier = Modifier,
) {
```

Add import:

```kotlin
import com.clothes.app.GoogleAuthClient
```

Replace the `ClozCard` content in `LoginScreen` with:

```kotlin
                Text("登录后保存你的身型档案、衣橱和推荐记录", color = ClozColors.Ink, fontWeight = FontWeight.SemiBold)
                ClozPrimaryButton(
                    text = if (state.isSigningIn) "正在连接 Google..." else "使用 Google 登录",
                    enabled = !state.isSigningIn,
                    onClick = { viewModel.signInWithGoogle(googleAuthClient) },
                )
                Text(
                    "继续即表示你同意《用户协议》与《隐私政策》",
                    modifier = Modifier.fillMaxWidth(),
                    color = ClozColors.Muted,
                    textAlign = TextAlign.Center,
                    style = MaterialTheme.typography.labelSmall,
                )
```

Remove unused imports from `OnboardingScreens.kt`: `KeyboardOptions`, `OutlinedTextField`, `OutlinedTextFieldDefaults`, and `KeyboardType` if no longer used elsewhere in the file.

- [ ] **Step 2: Add logout action to profile screen**

In `TabScreens.kt`, find `ProfileScreen`. Add a visible current-user label near the profile header:

```kotlin
        item {
            Text(
                state.currentUser?.email ?: "未登录",
                color = ClozColors.Muted,
                style = MaterialTheme.typography.bodySmall,
            )
        }
```

Add a logout menu row or button near the existing settings rows:

```kotlin
        item {
            ClozGhostButton("退出登录", onClick = viewModel::logout)
        }
```

If `ClozGhostButton` is not already imported in `TabScreens.kt`, add:

```kotlin
import com.clothes.app.ui.components.ClozGhostButton
```

- [ ] **Step 3: Compile Android**

Run:

```bash
cd android
.\gradlew.bat :app:compileDebugKotlin
```

Expected: BUILD SUCCESSFUL.

- [ ] **Step 4: Commit login UI**

Run:

```bash
git add android/app/src/main/kotlin/com/clothes/app/ui/screens/OnboardingScreens.kt android/app/src/main/kotlin/com/clothes/app/ui/screens/TabScreens.kt
git commit -m "feat: update android login ui"
```

---

### Task 7: Documentation And Final Verification

**Files:**
- Modify: `README.md`
- Verify: backend and Android commands

- [ ] **Step 1: Document backend Google auth config**

Add to the Python backend configuration section in `README.md`:

```markdown
Google 登录配置：

```env
STYLE_BACKEND_GOOGLE_CLIENT_ID=your-web-client-id.apps.googleusercontent.com
STYLE_BACKEND_AUTH_STORE_PATH=backend/storage/auth-store.json
STYLE_BACKEND_AUTH_SESSION_MAX_AGE_DAYS=30
```

Android 端的 `android/app/src/main/res/values/strings.xml` 也需要把 `google_web_client_id` 设置为同一个 Web Client ID。Google Cloud Console 中需要配置 Android OAuth Client，并加入调试/发布证书 SHA 指纹。
```

- [ ] **Step 2: Run backend tests**

Run:

```bash
cd backend
python -m pytest -q
```

Expected: PASS.

- [ ] **Step 3: Run Android compile**

Run:

```bash
cd android
.\gradlew.bat :app:compileDebugKotlin
```

Expected: BUILD SUCCESSFUL.

- [ ] **Step 4: Check full git diff**

Run:

```bash
git diff --stat
git status --short
```

Expected: only Google login files, plan/spec docs, and README are changed or staged for this feature. Existing unrelated working-tree changes may still appear; do not revert them.

- [ ] **Step 5: Commit documentation**

Run:

```bash
git add README.md
git commit -m "docs: document google login setup"
```

---

## Self-Review Notes

- Spec coverage: Android Credential Manager, backend ID token verification, session persistence, auth endpoints, config, error handling, tests, and docs all map to tasks above.
- Placeholder scan: The only placeholder value is the deliberate `google_web_client_id` replacement string in Android resources; runtime handles it with a user-facing configuration error.
- Type consistency: Backend uses `id_token`, `expires_at`, and snake_case JSON. Android parser maps those to `idToken`, `expiresAt`, and camelCase data classes.
