# Full Product Backend Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace Android mock-only product surfaces with Python backend-backed profile, home, inspiration, and favorites flows while preserving the existing style task, wardrobe, auth, and try-on paths.

**Architecture:** Add product-surface schemas, repositories, and FastAPI routes in the Python backend, with in-memory repositories wired through `AppContainer`. Then add Android JSON models/parsers/API methods and update the ViewModel/screens to render backend data with local visual fallbacks only for failures or missing images.

**Tech Stack:** FastAPI, Pydantic v2, pytest/TestClient, Kotlin, Jetpack Compose, Android `HttpURLConnection`, Gradle.

---

## File Structure

Backend:

- Create: `backend/app/schemas/product.py` for `StyleProfileView`, `HomeView`, `InspirationLook`, and favorite schemas.
- Create: `backend/app/providers/product_content.py` for seeded profile, inspiration, favorite, and home repositories.
- Modify: `backend/app/providers/persistence.py` to expose recent completed tasks from `InMemoryTaskRepository`.
- Modify: `backend/app/services/task_service.py` to expose recent completed tasks.
- Modify: `backend/app/services/container.py` to instantiate product repositories.
- Modify: `backend/app/api/routes.py` to add `/api/v1/profile`, `/api/v1/home`, `/api/v1/inspirations`, and `/api/v1/favorites`.
- Test: `backend/tests/test_product_surfaces.py` for API contracts and scoping.

Android:

- Modify: `android/app/build.gradle` to add JVM unit test dependencies for parser tests.
- Create: `android/app/src/test/kotlin/com/clothes/app/ProductParsingTest.kt` for new JSON parser behavior.
- Modify: `android/app/src/main/kotlin/com/clothes/app/StyleModels.kt` to add backend product surface models.
- Modify: `android/app/src/main/kotlin/com/clothes/app/StyleApi.kt` to add product API calls and parsers.
- Modify: `android/app/src/main/kotlin/com/clothes/app/StyleViewModel.kt` to load product surfaces and update style profile.
- Modify: `android/app/src/main/kotlin/com/clothes/app/ui/screens/TabScreens.kt` to replace normal `DemoLooks` and `DemoFavorites` reads.
- Modify: `android/app/src/main/kotlin/com/clothes/app/ui/screens/OnboardingScreens.kt` to render backend feature profile data and submit style profile updates.
- Modify: `android/app/src/main/kotlin/com/clothes/app/ui/screens/DetailScreens.kt` to support favorite actions where already exposed by UI buttons.

---

### Task 1: Backend Product Surface Contract Tests

**Files:**
- Create: `backend/tests/test_product_surfaces.py`

- [ ] **Step 1: Write the failing anonymous profile and seeded content tests**

Add this file with the first group of tests:

```python
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
```

- [ ] **Step 2: Run the contract tests and verify they fail for missing routes**

Run:

```powershell
cd backend
python -m pytest tests/test_product_surfaces.py::test_profile_returns_anonymous_default tests/test_product_surfaces.py::test_home_returns_seeded_recommendations_without_tasks tests/test_product_surfaces.py::test_inspirations_can_filter_by_scene -q
```

Expected: all three tests fail with `404 Not Found`.

- [ ] **Step 3: Commit only the failing tests**

Run:

```powershell
git add backend/tests/test_product_surfaces.py
git commit -m "test: define product surface api contracts"
```

---

### Task 2: Backend Schemas, Seed Repositories, And Read Routes

**Files:**
- Create: `backend/app/schemas/product.py`
- Create: `backend/app/providers/product_content.py`
- Modify: `backend/app/providers/persistence.py`
- Modify: `backend/app/services/task_service.py`
- Modify: `backend/app/services/container.py`
- Modify: `backend/app/api/routes.py`
- Test: `backend/tests/test_product_surfaces.py`

- [ ] **Step 1: Add product Pydantic schemas**

Create `backend/app/schemas/product.py`:

```python
from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

from app.schemas.auth import PublicUser
from app.schemas.domain import Scene


class FeatureMetric(BaseModel):
    label: str
    value: str


class StyleProfileUpdate(BaseModel):
    display_name: str | None = Field(default=None, max_length=80)
    height_cm: int | None = Field(default=None, ge=100, le=230)
    weight_kg: int | None = Field(default=None, ge=25, le=200)
    body_shape: str | None = Field(default=None, max_length=40)
    skin_tone: str | None = Field(default=None, max_length=40)
    hair_tone: str | None = Field(default=None, max_length=40)
    style_keywords: list[str] = Field(default_factory=list, max_length=12)


class StyleProfileView(StyleProfileUpdate):
    display_name: str = "Style User"
    feature_metrics: list[FeatureMetric] = Field(default_factory=list)


class ProfileView(BaseModel):
    user: PublicUser | None
    style_profile: StyleProfileView


class FeatureSummary(BaseModel):
    score: float = Field(ge=0, le=1)
    title: str
    summary: str


class HomeRecommendation(BaseModel):
    recommendation_id: str
    title: str
    scene: Scene
    score: float = Field(ge=0, le=1)
    image_url: str | None = None
    source_task_id: str | None = None


class TodaySuggestion(BaseModel):
    title: str
    body: str


class HomeView(BaseModel):
    feature_summary: FeatureSummary
    recommendations: list[HomeRecommendation]
    today_suggestion: TodaySuggestion
    backend_status: dict[str, Any]


class InspirationLook(BaseModel):
    inspiration_id: str
    title: str
    scene: Scene
    palette: str
    note: str
    score: float = Field(ge=0, le=1)
    image_url: str | None = None
    favorite_id: str | None = None


class InspirationPage(BaseModel):
    items: list[InspirationLook]
    next_cursor: str | None = None


class FavoriteType(StrEnum):
    outfit = "outfit"
    item = "item"
    inspiration = "inspiration"


class FavoriteCreate(BaseModel):
    favorite_type: FavoriteType
    target_id: str = Field(min_length=1, max_length=160)
    snapshot: dict[str, Any] = Field(default_factory=dict)


class FavoriteView(FavoriteCreate):
    favorite_id: str
    owner_id: str | None = None
```

- [ ] **Step 2: Add in-memory product repositories**

Create `backend/app/providers/product_content.py` with deterministic seed data and scoped favorite/profile stores:

```python
from __future__ import annotations

from dataclasses import dataclass, field
from uuid import uuid4

from app.schemas.domain import Scene
from app.schemas.product import (
    FavoriteCreate,
    FavoriteType,
    FavoriteView,
    FeatureMetric,
    FeatureSummary,
    HomeRecommendation,
    HomeView,
    InspirationLook,
    InspirationPage,
    StyleProfileUpdate,
    StyleProfileView,
    TodaySuggestion,
)
from app.schemas.results import StyleTaskView


def default_profile(display_name: str = "Style User") -> StyleProfileView:
    return StyleProfileView(
        display_name=display_name,
        height_cm=168,
        weight_kg=50,
        body_shape="pear",
        skin_tone="warm fair",
        hair_tone="dark brown",
        style_keywords=["clean", "commute", "proportion"],
        feature_metrics=[
            FeatureMetric(label="Height", value="168cm"),
            FeatureMetric(label="Body shape", value="Pear"),
            FeatureMetric(label="Waist hip", value="0.72"),
            FeatureMetric(label="Hair tone", value="Dark brown"),
        ],
    )


SEEDED_INSPIRATIONS = [
    InspirationLook(inspiration_id="commute-clean-1", title="Clean commute layers", scene=Scene.commute, palette="ivory / denim", note="Light outerwear and straight pants keep the line clean.", score=0.92),
    InspirationLook(inspiration_id="date-soft-1", title="Soft date texture", scene=Scene.date, palette="cream / mist pink", note="Soft knits and waist definition make the look gentle.", score=0.89),
    InspirationLook(inspiration_id="travel-easy-1", title="Easy travel shape", scene=Scene.travel, palette="khaki / gray", note="Comfortable pieces keep movement simple.", score=0.87),
    InspirationLook(inspiration_id="daily-minimal-1", title="Minimal daily contrast", scene=Scene.daily, palette="black / white", note="High contrast basics are easy to reuse.", score=0.91),
]


@dataclass
class ProfileRepository:
    profiles: dict[str | None, StyleProfileView] = field(default_factory=dict)

    def get(self, owner_id: str | None, display_name: str = "Style User") -> StyleProfileView:
        return self.profiles.get(owner_id) or default_profile(display_name)

    def update(self, owner_id: str | None, update: StyleProfileUpdate, display_name: str = "Style User") -> StyleProfileView:
        current = self.get(owner_id, display_name)
        next_profile = current.model_copy(update=update.model_dump(exclude_unset=True))
        metrics = [
            FeatureMetric(label="Height", value=f"{next_profile.height_cm or 168}cm"),
            FeatureMetric(label="Body shape", value=next_profile.body_shape or "pear"),
            FeatureMetric(label="Skin tone", value=next_profile.skin_tone or "warm fair"),
            FeatureMetric(label="Hair tone", value=next_profile.hair_tone or "dark brown"),
        ]
        next_profile = next_profile.model_copy(update={"feature_metrics": metrics})
        self.profiles[owner_id] = next_profile
        return next_profile


@dataclass
class FavoriteRepository:
    favorites: dict[str, FavoriteView] = field(default_factory=dict)

    def list_for_owner(self, owner_id: str | None, favorite_type: FavoriteType | None = None) -> list[FavoriteView]:
        return [
            favorite
            for favorite in self.favorites.values()
            if favorite.owner_id == owner_id and (favorite_type is None or favorite.favorite_type == favorite_type)
        ]

    def save(self, owner_id: str | None, create: FavoriteCreate) -> FavoriteView:
        existing = next(
            (
                favorite
                for favorite in self.favorites.values()
                if favorite.owner_id == owner_id and favorite.favorite_type == create.favorite_type and favorite.target_id == create.target_id
            ),
            None,
        )
        favorite = FavoriteView(
            favorite_id=existing.favorite_id if existing else f"fav_{uuid4().hex[:16]}",
            owner_id=owner_id,
            **create.model_dump(),
        )
        self.favorites[favorite.favorite_id] = favorite
        return favorite

    def delete(self, owner_id: str | None, favorite_id: str) -> None:
        favorite = self.favorites.get(favorite_id)
        if favorite is None:
            raise KeyError(favorite_id)
        if favorite.owner_id != owner_id:
            raise PermissionError(favorite_id)
        del self.favorites[favorite_id]


@dataclass
class InspirationRepository:
    def list(self, *, scene: Scene | None, favorite_ids_by_target: dict[str, str]) -> InspirationPage:
        items = [item for item in SEEDED_INSPIRATIONS if scene is None or item.scene == scene]
        return InspirationPage(
            items=[item.model_copy(update={"favorite_id": favorite_ids_by_target.get(item.inspiration_id)}) for item in items],
            next_cursor=None,
        )


def build_home_view(*, profile: StyleProfileView, tasks: list[StyleTaskView], settings_status: dict) -> HomeView:
    recommendations = []
    for task in tasks:
        if task.result and task.result.outfit:
            recommendations.append(
                HomeRecommendation(
                    recommendation_id=task.result.outfit.candidate_id,
                    title=task.result.outfit.title,
                    scene=task.request.scene,
                    score=task.result.outfit.score,
                    image_url=task.result.try_on_image_url,
                    source_task_id=task.task_id,
                )
            )
    if not recommendations:
        recommendations = [
            HomeRecommendation(recommendation_id=item.inspiration_id, title=item.title, scene=item.scene, score=item.score, image_url=item.image_url)
            for item in SEEDED_INSPIRATIONS[:3]
        ]
    return HomeView(
        feature_summary=FeatureSummary(score=0.92, title="Feature match", summary=", ".join(profile.style_keywords[:3])),
        recommendations=recommendations[:6],
        today_suggestion=TodaySuggestion(title="Today outfit suggestion", body="Light layers and clean proportions are a good default today."),
        backend_status=settings_status,
    )
```

- [ ] **Step 3: Wire repositories into the container**

Modify `TaskRepository` protocol in `backend/app/providers/persistence.py`:

```python
def list_recent_completed(self, limit: int = 6) -> list[StyleTaskView]:
    ...
```

Add to `InMemoryTaskRepository`:

```python
def list_recent_completed(self, limit: int = 6) -> list[StyleTaskView]:
    completed = [
        task
        for task in self.tasks.values()
        if task.result is not None and task.status in {TaskStatus.succeeded, TaskStatus.partial_succeeded}
    ]
    completed.sort(key=lambda task: task.updated_at, reverse=True)
    return completed[:limit]
```

Modify `backend/app/services/task_service.py`:

```python
def recent_completed_tasks(self, limit: int = 6) -> list[StyleTaskView]:
    return self.repository.list_recent_completed(limit)
```

Modify `backend/app/services/container.py` imports:

```python
from app.providers.product_content import FavoriteRepository, InspirationRepository, ProfileRepository
```

Inside `AppContainer.__init__`, after `self.wardrobe_repository = InMemoryWardrobeRepository()`:

```python
self.profile_repository = ProfileRepository()
self.favorite_repository = FavoriteRepository()
self.inspiration_repository = InspirationRepository()
```

- [ ] **Step 4: Add read routes**

Modify `backend/app/api/routes.py` imports:

```python
from app.schemas.product import FavoriteType, HomeView, InspirationPage, ProfileView, StyleProfileUpdate, StyleProfileView
from app.providers.product_content import build_home_view
```

Add helper functions near `_visible_wardrobe_items`:

```python
def _owner_id(user: PublicUser | None) -> str | None:
    return user.user_id if user else None


def _display_name(user: PublicUser | None) -> str:
    return user.name if user else "Style User"
```

Add routes:

```python
@router.get("/api/v1/profile", response_model=ProfileView)
async def get_profile(
    container: Annotated[AppContainer, Depends(container_dependency)],
    user: Annotated[PublicUser | None, Depends(current_user)],
) -> ProfileView:
    profile = container.profile_repository.get(_owner_id(user), _display_name(user))
    return ProfileView(user=user, style_profile=profile)


@router.put("/api/v1/profile/style", response_model=StyleProfileView)
async def update_style_profile(
    payload: StyleProfileUpdate,
    container: Annotated[AppContainer, Depends(container_dependency)],
    user: Annotated[PublicUser | None, Depends(current_user)],
) -> StyleProfileView:
    return container.profile_repository.update(_owner_id(user), payload, _display_name(user))


@router.get("/api/v1/home", response_model=HomeView)
async def get_home(
    container: Annotated[AppContainer, Depends(container_dependency)],
    user: Annotated[PublicUser | None, Depends(current_user)],
) -> HomeView:
    owner_id = _owner_id(user)
    profile = container.profile_repository.get(owner_id, _display_name(user))
    return build_home_view(
        profile=profile,
        tasks=container.task_service.recent_completed_tasks(),
        settings_status={
            "ok": True,
            "search_provider": container.settings.search_provider,
            "image_provider": container.settings.image_provider,
            "model_provider": container.settings.model_provider,
        },
    )


@router.get("/api/v1/inspirations", response_model=InspirationPage)
async def list_inspirations(
    container: Annotated[AppContainer, Depends(container_dependency)],
    user: Annotated[PublicUser | None, Depends(current_user)],
    scene: Scene | None = None,
) -> InspirationPage:
    favorites = container.favorite_repository.list_for_owner(_owner_id(user), FavoriteType.inspiration)
    favorite_ids_by_target = {favorite.target_id: favorite.favorite_id for favorite in favorites}
    return container.inspiration_repository.list(scene=scene, favorite_ids_by_target=favorite_ids_by_target)
```

- [ ] **Step 5: Run the first backend tests and verify they pass**

Run:

```powershell
cd backend
python -m pytest tests/test_product_surfaces.py::test_profile_returns_anonymous_default tests/test_product_surfaces.py::test_home_returns_seeded_recommendations_without_tasks tests/test_product_surfaces.py::test_inspirations_can_filter_by_scene -q
```

Expected: `3 passed`.

- [ ] **Step 6: Commit the backend read surface**

Run:

```powershell
git add backend/app/schemas/product.py backend/app/providers/product_content.py backend/app/providers/persistence.py backend/app/services/task_service.py backend/app/services/container.py backend/app/api/routes.py backend/tests/test_product_surfaces.py
git commit -m "feat: add product surface read APIs"
```

---

### Task 3: Backend Profile Update, Favorites, And Home History

**Files:**
- Modify: `backend/tests/test_product_surfaces.py`
- Modify: `backend/app/api/routes.py`
- Modify: `backend/app/providers/product_content.py`

- [ ] **Step 1: Add failing tests for update, favorites, scoping, and task-backed home**

Append tests to `backend/tests/test_product_surfaces.py`:

```python
from app.providers.auth import GoogleProfile
from app.providers.google_auth import GoogleIdTokenVerifier
from app.schemas.domain import Budget, OutfitCandidate, StylePreferences, StyleTaskRequest, TaskStatus
from app.schemas.results import StyleTaskResult


class FakeGoogleVerifier(GoogleIdTokenVerifier):
    def __init__(self, sub: str = "sub-1", email: str = "one@example.com") -> None:
        self.sub = sub
        self.email = email

    def verify(self, id_token: str) -> GoogleProfile:
        return GoogleProfile(sub=self.sub, email=self.email, email_verified=True, name=self.email.split("@")[0])


def login(client: TestClient, sub: str, email: str) -> str:
    container = get_container()
    container.google_id_token_verifier = FakeGoogleVerifier(sub, email)
    response = client.post("/api/v1/auth/google", json={"id_token": "header.payload.signature"})
    assert response.status_code == 200
    return response.json()["session"]["token"]


def test_profile_update_is_scoped_to_user(tmp_path):
    client = product_client(tmp_path)
    first = login(client, "sub-a", "first@example.com")
    second = login(client, "sub-b", "second@example.com")

    update = {"height_cm": 171, "body_shape": "hourglass", "style_keywords": ["minimal", "date"]}
    first_response = client.put("/api/v1/profile/style", json=update, headers={"Authorization": f"Bearer {first}"})
    second_response = client.get("/api/v1/profile", headers={"Authorization": f"Bearer {second}"})

    assert first_response.status_code == 200
    assert first_response.json()["height_cm"] == 171
    assert second_response.json()["style_profile"]["height_cm"] == 168


def test_favorites_are_scoped_and_can_be_deleted(tmp_path):
    client = product_client(tmp_path)
    first = login(client, "sub-a", "first@example.com")
    second = login(client, "sub-b", "second@example.com")

    created = client.post(
        "/api/v1/favorites",
        json={"favorite_type": "inspiration", "target_id": "commute-clean-1", "snapshot": {"title": "Clean commute layers"}},
        headers={"Authorization": f"Bearer {first}"},
    )
    favorite_id = created.json()["favorite_id"]

    first_list = client.get("/api/v1/favorites?type=inspiration", headers={"Authorization": f"Bearer {first}"})
    second_list = client.get("/api/v1/favorites?type=inspiration", headers={"Authorization": f"Bearer {second}"})
    blocked_delete = client.delete(f"/api/v1/favorites/{favorite_id}", headers={"Authorization": f"Bearer {second}"})
    deleted = client.delete(f"/api/v1/favorites/{favorite_id}", headers={"Authorization": f"Bearer {first}"})

    assert created.status_code == 200
    assert [item["favorite_id"] for item in first_list.json()] == [favorite_id]
    assert second_list.json() == []
    assert blocked_delete.status_code == 403
    assert deleted.status_code == 200
    assert deleted.json() == {"ok": True}


def test_anonymous_favorites_round_trip(tmp_path):
    client = product_client(tmp_path)

    created = client.post("/api/v1/favorites", json={"favorite_type": "item", "target_id": "item-1", "snapshot": {"title": "White shirt"}})
    listed = client.get("/api/v1/favorites?type=item")

    assert created.status_code == 200
    assert listed.status_code == 200
    assert listed.json()[0]["target_id"] == "item-1"


def test_home_can_include_completed_style_task(tmp_path):
    client = product_client(tmp_path)
    container = get_container()
    task = container.task_service.create_task(
        StyleTaskRequest(
            photo_url="https://example.com/person.jpg",
            photo_object_key="uploads/person.jpg",
            budget=Budget(min=300, max=900),
            preferences=StylePreferences(liked_style="clean"),
        )
    )
    outfit = OutfitCandidate(
        candidate_id="outfit_home_1",
        title="Backend completed outfit",
        items=[],
        total_price=0,
        score=0.91,
        score_breakdown={"coherence": 0.91},
        why_this_works=["Recent result"],
    )
    container.task_service.repository.complete(
        task.task_id,
        StyleTaskResult(
            task_id=task.task_id,
            status=TaskStatus.succeeded,
            outfit=outfit,
            try_on_image_url="https://example.com/tryon.png",
        ),
    )

    response = client.get("/api/v1/home")

    assert response.status_code == 200
    assert response.json()["recommendations"][0]["source_task_id"] == task.task_id
```

- [ ] **Step 2: Run the new tests and verify expected failures**

Run:

```powershell
cd backend
python -m pytest tests/test_product_surfaces.py::test_profile_update_is_scoped_to_user tests/test_product_surfaces.py::test_favorites_are_scoped_and_can_be_deleted tests/test_product_surfaces.py::test_anonymous_favorites_round_trip -q
```

Expected: failures for missing `/api/v1/favorites` routes. Profile update and task-backed home should pass from Task 2.

- [ ] **Step 3: Add favorite routes**

Modify imports in `backend/app/api/routes.py`:

```python
from app.schemas.product import FavoriteCreate, FavoriteType, FavoriteView
```

Add routes:

```python
@router.get("/api/v1/favorites", response_model=list[FavoriteView])
async def list_favorites(
    container: Annotated[AppContainer, Depends(container_dependency)],
    user: Annotated[PublicUser | None, Depends(current_user)],
    type: FavoriteType | None = None,
) -> list[FavoriteView]:
    return container.favorite_repository.list_for_owner(_owner_id(user), type)


@router.post("/api/v1/favorites", response_model=FavoriteView)
async def save_favorite(
    payload: FavoriteCreate,
    container: Annotated[AppContainer, Depends(container_dependency)],
    user: Annotated[PublicUser | None, Depends(current_user)],
) -> FavoriteView:
    return container.favorite_repository.save(_owner_id(user), payload)


@router.delete("/api/v1/favorites/{favorite_id}")
async def delete_favorite(
    favorite_id: str,
    container: Annotated[AppContainer, Depends(container_dependency)],
    user: Annotated[PublicUser | None, Depends(current_user)],
) -> dict[str, bool]:
    try:
        container.favorite_repository.delete(_owner_id(user), favorite_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Favorite not found") from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail="Favorite is not available") from exc
    return {"ok": True}
```

- [ ] **Step 4: Run backend product tests**

Run:

```powershell
cd backend
python -m pytest tests/test_product_surfaces.py -q
```

Expected: all product surface tests pass.

- [ ] **Step 5: Run existing backend tests**

Run:

```powershell
cd backend
python -m pytest tests/test_auth.py tests/test_agent_graph.py -q
```

Expected: all existing tests pass.

- [ ] **Step 6: Commit backend product mutations**

Run:

```powershell
git add backend/app/api/routes.py backend/app/providers/product_content.py backend/tests/test_product_surfaces.py
git commit -m "feat: add profile favorites and home history"
```

---

### Task 4: Android Product JSON Models And API Methods

**Files:**
- Modify: `android/app/build.gradle`
- Create: `android/app/src/test/kotlin/com/clothes/app/ProductParsingTest.kt`
- Modify: `android/app/src/main/kotlin/com/clothes/app/StyleModels.kt`
- Modify: `android/app/src/main/kotlin/com/clothes/app/StyleApi.kt`

- [ ] **Step 1: Add Android JVM test dependencies**

Modify `android/app/build.gradle` dependencies:

```gradle
testImplementation "junit:junit:4.13.2"
testImplementation "org.json:json:20240303"
```

- [ ] **Step 2: Write failing parser tests**

Create `android/app/src/test/kotlin/com/clothes/app/ProductParsingTest.kt`:

```kotlin
package com.clothes.app

import org.json.JSONObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class ProductParsingTest {
    @Test
    fun parsesProfileView() {
        val profile = parseProfileView(
            JSONObject(
                """
                {
                  "user": null,
                  "style_profile": {
                    "display_name": "Style User",
                    "height_cm": 168,
                    "weight_kg": 50,
                    "body_shape": "pear",
                    "skin_tone": "warm fair",
                    "hair_tone": "dark brown",
                    "style_keywords": ["clean", "commute"],
                    "feature_metrics": [{"label": "Height", "value": "168cm"}]
                  }
                }
                """.trimIndent(),
            ),
        )

        assertNull(profile.user)
        assertEquals("Style User", profile.styleProfile.displayName)
        assertEquals("Height", profile.styleProfile.featureMetrics.first().label)
    }

    @Test
    fun parsesHomeView() {
        val home = parseHomeView(
            JSONObject(
                """
                {
                  "feature_summary": {"score": 0.92, "title": "Feature match", "summary": "clean"},
                  "recommendations": [{"recommendation_id": "rec1", "title": "Clean commute", "scene": "commute", "score": 0.91, "image_url": null, "source_task_id": null}],
                  "today_suggestion": {"title": "Today", "body": "Light layers"},
                  "backend_status": {"ok": true}
                }
                """.trimIndent(),
            ),
        )

        assertEquals(0.92, home.featureSummary.score, 0.001)
        assertEquals("Clean commute", home.recommendations.first().title)
    }

    @Test
    fun parsesInspirationsAndFavorites() {
        val page = parseInspirationPage(
            JSONObject(
                """
                {"items": [{"inspiration_id": "look1", "title": "Look", "scene": "daily", "palette": "black / white", "note": "Clean", "score": 0.9, "image_url": null, "favorite_id": "fav1"}], "next_cursor": null}
                """.trimIndent(),
            ),
        )
        val favorite = parseFavorite(
            JSONObject("""{"favorite_id": "fav1", "owner_id": null, "favorite_type": "inspiration", "target_id": "look1", "snapshot": {"title": "Look"}}"""),
        )

        assertEquals("look1", page.items.first().inspirationId)
        assertEquals("fav1", favorite.favoriteId)
    }
}
```

- [ ] **Step 3: Run parser tests and verify unresolved reference failures**

Run:

```powershell
cd android
.\gradlew.bat :app:testDebugUnitTest --tests "com.clothes.app.ProductParsingTest" --no-daemon
```

Expected: Kotlin compilation fails because `parseProfileView`, `parseHomeView`, `parseInspirationPage`, and `parseFavorite` do not exist.

- [ ] **Step 4: Add Android models**

Modify `android/app/src/main/kotlin/com/clothes/app/StyleModels.kt` by adding:

```kotlin
data class FeatureMetric(val label: String, val value: String)

data class StyleProfile(
    val displayName: String,
    val heightCm: Int?,
    val weightKg: Int?,
    val bodyShape: String?,
    val skinTone: String?,
    val hairTone: String?,
    val styleKeywords: List<String>,
    val featureMetrics: List<FeatureMetric>,
)

data class ProfileView(val user: PublicUser?, val styleProfile: StyleProfile)

data class FeatureSummary(val score: Double, val title: String, val summary: String)

data class HomeRecommendation(
    val recommendationId: String,
    val title: String,
    val scene: String,
    val score: Double,
    val imageUrl: String?,
    val sourceTaskId: String?,
)

data class TodaySuggestion(val title: String, val body: String)

data class HomeView(
    val featureSummary: FeatureSummary,
    val recommendations: List<HomeRecommendation>,
    val todaySuggestion: TodaySuggestion,
    val backendStatus: Map<String, String>,
)

data class InspirationPage(val items: List<InspirationLook>, val nextCursor: String?)

data class FavoriteView(
    val favoriteId: String,
    val ownerId: String?,
    val favoriteType: String,
    val targetId: String,
    val snapshotTitle: String?,
)
```

Extend existing `InspirationLook` with:

```kotlin
val inspirationId: String = "",
val imageUrl: String? = null,
val favoriteId: String? = null,
```

- [ ] **Step 5: Add StyleApi methods and parsers**

Modify `android/app/src/main/kotlin/com/clothes/app/StyleApi.kt` with methods:

```kotlin
suspend fun getProfile(): ProfileView = withContext(Dispatchers.IO) {
    val connection = openConnection("/api/v1/profile", "GET")
    try { parseProfileView(JSONObject(readResponse(connection))) } finally { connection.disconnect() }
}

suspend fun updateStyleProfile(profile: StyleProfile): StyleProfile = withContext(Dispatchers.IO) {
    val connection = openConnection("/api/v1/profile/style", "PUT").apply {
        doOutput = true
        setRequestProperty("Content-Type", "application/json")
    }
    try {
        val body = JSONObject()
            .put("display_name", profile.displayName)
            .put("height_cm", profile.heightCm)
            .put("weight_kg", profile.weightKg)
            .put("body_shape", profile.bodyShape)
            .put("skin_tone", profile.skinTone)
            .put("hair_tone", profile.hairTone)
            .put("style_keywords", JSONArray(profile.styleKeywords))
            .toString()
            .toByteArray(Charsets.UTF_8)
        connection.outputStream.use { it.write(body) }
        parseStyleProfile(JSONObject(readResponse(connection)))
    } finally { connection.disconnect() }
}

suspend fun getHome(): HomeView = withContext(Dispatchers.IO) {
    val connection = openConnection("/api/v1/home", "GET")
    try { parseHomeView(JSONObject(readResponse(connection))) } finally { connection.disconnect() }
}

suspend fun getInspirations(scene: String? = null): InspirationPage = withContext(Dispatchers.IO) {
    val path = if (scene.isNullOrBlank()) "/api/v1/inspirations" else "/api/v1/inspirations?scene=$scene"
    val connection = openConnection(path, "GET")
    try { parseInspirationPage(JSONObject(readResponse(connection))) } finally { connection.disconnect() }
}

suspend fun getFavorites(type: String): List<FavoriteView> = withContext(Dispatchers.IO) {
    val connection = openConnection("/api/v1/favorites?type=$type", "GET")
    try { parseFavorites(JSONArray(readResponse(connection))) } finally { connection.disconnect() }
}
```

Add parser functions:

```kotlin
fun parseProfileView(json: JSONObject): ProfileView = ProfileView(
    user = json.optJSONObject("user")?.let(::parsePublicUser),
    styleProfile = parseStyleProfile(json.getJSONObject("style_profile")),
)

fun parseStyleProfile(json: JSONObject): StyleProfile = StyleProfile(
    displayName = json.optString("display_name"),
    heightCm = json.optNullableInt("height_cm"),
    weightKg = json.optNullableInt("weight_kg"),
    bodyShape = json.optNullableString("body_shape"),
    skinTone = json.optNullableString("skin_tone"),
    hairTone = json.optNullableString("hair_tone"),
    styleKeywords = json.optJSONArray("style_keywords").toStringList(),
    featureMetrics = json.optJSONArray("feature_metrics").toObjectList { item ->
        FeatureMetric(item.optString("label"), item.optString("value"))
    },
)

fun parseHomeView(json: JSONObject): HomeView = HomeView(
    featureSummary = json.getJSONObject("feature_summary").let { FeatureSummary(it.optDouble("score"), it.optString("title"), it.optString("summary")) },
    recommendations = json.optJSONArray("recommendations").toObjectList(::parseHomeRecommendation),
    todaySuggestion = json.getJSONObject("today_suggestion").let { TodaySuggestion(it.optString("title"), it.optString("body")) },
    backendStatus = json.optJSONObject("backend_status").toStringMap(),
)
```

Also add `parseHomeRecommendation`, `parseInspirationPage`, `parseFavorite`, `parseFavorites`, `JSONObject?.toStringMap()`, and `JSONObject.optNullableInt(name)`.

- [ ] **Step 6: Run parser tests and verify green**

Run:

```powershell
cd android
.\gradlew.bat :app:testDebugUnitTest --tests "com.clothes.app.ProductParsingTest" --no-daemon
```

Expected: `BUILD SUCCESSFUL`.

- [ ] **Step 7: Commit Android model/API parsing**

Run:

```powershell
git add android/app/build.gradle android/app/src/test/kotlin/com/clothes/app/ProductParsingTest.kt android/app/src/main/kotlin/com/clothes/app/StyleModels.kt android/app/src/main/kotlin/com/clothes/app/StyleApi.kt
git commit -m "feat: add android product api models"
```

---

### Task 5: Android ViewModel And Screen Integration

**Files:**
- Modify: `android/app/src/main/kotlin/com/clothes/app/StyleViewModel.kt`
- Modify: `android/app/src/main/kotlin/com/clothes/app/ui/screens/TabScreens.kt`
- Modify: `android/app/src/main/kotlin/com/clothes/app/ui/screens/OnboardingScreens.kt`
- Modify: `android/app/src/main/kotlin/com/clothes/app/ui/screens/DetailScreens.kt`

- [ ] **Step 1: Extend UiState with product backend fields**

Modify `UiState` in `StyleModels.kt`:

```kotlin
val profileView: ProfileView? = null,
val homeView: HomeView? = null,
val inspirationPage: InspirationPage? = null,
val favoriteItems: List<FavoriteView> = emptyList(),
val isLoadingProfile: Boolean = false,
val isLoadingHome: Boolean = false,
val isLoadingInspirations: Boolean = false,
val isLoadingFavorites: Boolean = false,
```

- [ ] **Step 2: Add ViewModel product loaders**

Modify `StyleViewModel.kt`:

```kotlin
private fun refreshProductSurfaces() {
    refreshProfile()
    refreshHome()
}

fun refreshProfile() {
    if (_uiState.value.isLoadingProfile) return
    viewModelScope.launch {
        _uiState.update { it.copy(isLoadingProfile = true) }
        val result = runCatching { api.getProfile() }
        _uiState.update {
            it.copy(
                isLoadingProfile = false,
                profileView = result.getOrElse { _ -> it.profileView },
                currentUser = result.getOrNull()?.user ?: it.currentUser,
                notice = result.exceptionOrNull()?.message,
            )
        }
    }
}

fun refreshHome() {
    if (_uiState.value.isLoadingHome) return
    viewModelScope.launch {
        _uiState.update { it.copy(isLoadingHome = true) }
        val result = runCatching { api.getHome() }
        _uiState.update {
            it.copy(
                isLoadingHome = false,
                homeView = result.getOrElse { _ -> it.homeView },
                notice = result.exceptionOrNull()?.message,
            )
        }
    }
}

fun loadInspirations(scene: String? = null) {
    if (_uiState.value.isLoadingInspirations) return
    viewModelScope.launch {
        _uiState.update { it.copy(isLoadingInspirations = true) }
        val result = runCatching { api.getInspirations(scene) }
        _uiState.update {
            it.copy(
                isLoadingInspirations = false,
                inspirationPage = result.getOrElse { _ -> it.inspirationPage },
                notice = result.exceptionOrNull()?.message,
            )
        }
    }
}

fun loadFavorites(type: String = _uiState.value.favoritesTab.apiType) {
    if (_uiState.value.isLoadingFavorites) return
    viewModelScope.launch {
        _uiState.update { it.copy(isLoadingFavorites = true) }
        val result = runCatching { api.getFavorites(type) }
        _uiState.update {
            it.copy(
                isLoadingFavorites = false,
                favoriteItems = result.getOrElse { _ -> it.favoriteItems },
                notice = result.exceptionOrNull()?.message,
            )
        }
    }
}
```

Add `FavoriteTab.apiType` in `StyleModels.kt`:

```kotlin
val FavoriteTab.apiType: String
    get() = when (this) {
        FavoriteTab.Outfits -> "outfit"
        FavoriteTab.Items -> "item"
        FavoriteTab.Inspiration -> "inspiration"
    }
```

Call `refreshProductSurfaces()` in `init`, `finishOnboarding()`, and after successful login. Call `loadInspirations()` when navigating to `AppRoute.Inspiration`; call `loadFavorites()` when opening favorites or switching tabs.

- [ ] **Step 3: Replace home normal source with backend data**

In `HomeScreen`, use:

```kotlin
val home = state.homeView
val recommendations = home?.recommendations.orEmpty()
```

Render `recommendations` first. If empty, keep `DemoLooks.take(3)` as fallback. Replace the feature card score with `home?.featureSummary?.score ?: 0.92` and suggestion copy with `home?.todaySuggestion?.body ?: existing copy`.

- [ ] **Step 4: Replace inspiration normal source**

In `InspirationScreen`, use:

```kotlin
val looks = state.inspirationPage?.items ?: DemoLooks
```

Keep `DemoLooks` only as fallback. Existing `InspirationTile` can continue to accept `InspirationLook` after the model extension.

- [ ] **Step 5: Replace favorites normal source**

In `FavoritesScreen`, render `state.favoriteItems` when non-empty. For backend favorites, show `favorite.snapshotTitle ?: favorite.targetId` in cards. Keep `DemoFavorites` only when no backend favorite records exist.

- [ ] **Step 6: Replace profile and feature analysis data**

In `ProfileScreen`, use:

```kotlin
val profile = state.profileView?.styleProfile
Text(profile?.displayName ?: state.currentUser?.name ?: "Style User", ...)
Text(state.profileView?.user?.email ?: state.currentUser?.email ?: "Not signed in", ...)
```

In `FeatureAnalysisScreen`, use:

```kotlin
val profile = state.profileView?.styleProfile
val metrics = profile?.featureMetrics ?: DemoFeatureMetrics
val keywords = profile?.styleKeywords ?: DemoStyleKeywords
```

- [ ] **Step 7: Compile Android**

Run:

```powershell
cd android
.\gradlew.bat :app:assembleDebug --no-daemon
```

Expected: `BUILD SUCCESSFUL`.

- [ ] **Step 8: Commit Android screen integration**

Run:

```powershell
git add android/app/src/main/kotlin/com/clothes/app/StyleModels.kt android/app/src/main/kotlin/com/clothes/app/StyleViewModel.kt android/app/src/main/kotlin/com/clothes/app/ui/screens/TabScreens.kt android/app/src/main/kotlin/com/clothes/app/ui/screens/OnboardingScreens.kt android/app/src/main/kotlin/com/clothes/app/ui/screens/DetailScreens.kt
git commit -m "feat: connect product pages to backend"
```

---

### Task 6: End-To-End Verification

**Files:**
- No expected source edits unless verification exposes a defect.

- [ ] **Step 1: Run all backend tests**

Run:

```powershell
cd backend
python -m pytest -q
```

Expected: all tests pass.

- [ ] **Step 2: Run Android parser tests**

Run:

```powershell
cd android
.\gradlew.bat :app:testDebugUnitTest --tests "com.clothes.app.ProductParsingTest" --no-daemon
```

Expected: `BUILD SUCCESSFUL`.

- [ ] **Step 3: Build Android debug APK**

Run:

```powershell
cd android
.\gradlew.bat :app:assembleDebug --no-daemon
```

Expected: `BUILD SUCCESSFUL`.

- [ ] **Step 4: Run Python backend locally for smoke checks**

Run:

```powershell
cd backend
python -m uvicorn app.main:app --port 8000
```

In a second terminal, run:

```powershell
curl http://127.0.0.1:8000/api/v1/profile
curl http://127.0.0.1:8000/api/v1/home
curl http://127.0.0.1:8000/api/v1/inspirations
curl http://127.0.0.1:8000/api/v1/favorites?type=inspiration
```

Expected: every command returns HTTP 200 JSON.

- [ ] **Step 5: Final status check**

Run:

```powershell
git status --short
```

Expected: only intentional files from completed tasks are modified. Do not revert unrelated pre-existing worktree changes.
