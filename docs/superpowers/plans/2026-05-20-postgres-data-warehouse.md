# PostgreSQL Data Warehouse Persistence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build formal PostgreSQL persistence for auth users, sessions, style task request logs, task results, trace events, wardrobe items, favorite products, and saved looks.

**Architecture:** Keep the existing local development path when no `STYLE_BACKEND_POSTGRES_DSN` is configured, and switch the whole persistence set to Postgres when it is configured. Add a small favorites/saved-looks repository boundary so API routes do not know whether data is in memory or Postgres.

**Tech Stack:** FastAPI, Pydantic v2, psycopg 3, PostgreSQL JSONB, pytest, existing app container pattern.

---

## File Structure

- Modify `backend/migrations/001_initial.sql`
  Adds auth, session, favorite product, and uniqueness constraints for saved looks.
- Create `backend/app/schemas/favorites.py`
  Public request and response models for favorite products and saved looks.
- Modify `backend/app/providers/auth.py`
  Keep `AuthStore` as the local JSON implementation and add a small protocol shape through shared method names.
- Modify `backend/app/providers/persistence.py`
  Add repository protocols for wardrobe and favorites, add local in-memory favorites, and add task ownership support.
- Replace `backend/app/providers/postgres.py`
  Provide the Postgres connection helper plus concrete Postgres repositories for auth, task, wardrobe, trace, and favorites.
- Modify `backend/app/providers/tracing.py`
  Keep `TraceRecorder` stable and rely on the Postgres implementation from `providers/postgres.py`.
- Modify `backend/app/services/task_service.py`
  Thread task ownership through task creation and expose favorites/saved-look service methods.
- Modify `backend/app/services/container.py`
  Select local or Postgres persistence based on `STYLE_BACKEND_POSTGRES_DSN`.
- Modify `backend/app/api/routes.py`
  Pass the current user id when creating tasks and add favorite-product and saved-look routes.
- Create `backend/tests/test_favorites_repository.py`
  Local repository behavior tests.
- Create `backend/tests/test_favorites_api.py`
  API behavior tests with local repositories.
- Create `backend/tests/test_postgres_persistence.py`
  Postgres integration tests, skipped unless `STYLE_BACKEND_TEST_POSTGRES_DSN` is present.
- Modify `backend/README.md`
  Document the Postgres DSN and test DSN behavior.

---

### Task 1: Local Schema, Repository Interfaces, and Service Boundary

**Files:**
- Create: `backend/app/schemas/favorites.py`
- Modify: `backend/app/providers/persistence.py`
- Modify: `backend/app/services/task_service.py`
- Test: `backend/tests/test_favorites_repository.py`

- [ ] **Step 1: Write failing local repository tests**

Create `backend/tests/test_favorites_repository.py`:

```python
from __future__ import annotations

from app.providers.persistence import InMemoryFavoritesRepository, InMemoryTaskRepository
from app.schemas.domain import Budget, Marketplace, ProductCandidate, ProductCategory, Scene, StyleTaskRequest, TaskStatus
from app.schemas.favorites import FavoriteProductCreate
from app.schemas.quality import GateStatus, QualityGateReport, RecommendationReport
from app.schemas.results import StyleTaskResult


def product(product_id: str = "tmall_100") -> ProductCandidate:
    return ProductCandidate(
        product_id=product_id,
        marketplace=Marketplace.tmall,
        category=ProductCategory.top,
        title="White shirt",
        price=199,
        price_text="CNY 199",
        image_url="https://example.com/shirt.jpg",
        product_url="https://detail.tmall.com/item.htm?id=100",
        shop_name="Example Shop",
        sizes=["M"],
        colors=["white"],
        style_tags=["clean"],
        fit_tags=["regular"],
        source_reliability=0.91,
        score=0.88,
        risk_flags=[],
        raw={"source": "test"},
    )


def request() -> StyleTaskRequest:
    return StyleTaskRequest(
        photo_url="https://example.com/person.jpg",
        photo_object_key="uploads/person.jpg",
        scene=Scene.daily,
        budget=Budget(min=300, max=800),
        marketplaces=[Marketplace.tmall],
    )


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


def test_in_memory_favorites_are_idempotent_and_user_scoped() -> None:
    repo = InMemoryFavoritesRepository()
    payload = FavoriteProductCreate(**product().model_dump(), source_task_id="task_1")

    first = repo.save_product("user_a", payload)
    duplicate = repo.save_product("user_a", payload)
    other_user = repo.save_product("user_b", payload)

    assert duplicate.favorite_id == first.favorite_id
    assert other_user.favorite_id != first.favorite_id
    assert [item.favorite_id for item in repo.list_products("user_a")] == [first.favorite_id]
    assert [item.favorite_id for item in repo.list_products("user_b")] == [other_user.favorite_id]
    assert repo.delete_product("user_a", other_user.favorite_id) is False
    assert repo.delete_product("user_a", first.favorite_id) is True
    assert repo.list_products("user_a") == []


def test_task_repository_tracks_owner_without_exposing_it_in_task_view() -> None:
    repo = InMemoryTaskRepository()

    task = repo.create("task_1", request(), user_id="user_a")

    assert task.task_id == "task_1"
    assert repo.owner_id("task_1") == "user_a"
    assert "user_id" not in task.model_dump()


def test_in_memory_saved_looks_are_idempotent_and_user_scoped() -> None:
    task_repo = InMemoryTaskRepository()
    favorites_repo = InMemoryFavoritesRepository()
    task = task_repo.create("task_1", request(), user_id="user_a")
    result = StyleTaskResult(
        task_id=task.task_id,
        status=TaskStatus.partial_succeeded,
        outfit=None,
        recommendation_report=recommendation_report(),
        user_message="partial",
    )
    task_repo.complete(task.task_id, result)

    look = favorites_repo.save_look("user_a", task_repo.get(task.task_id))
    duplicate = favorites_repo.save_look("user_a", task_repo.get(task.task_id))

    assert duplicate.look_id == look.look_id
    assert look.user_id == "user_a"
    assert look.source_task_id == "task_1"
    assert favorites_repo.list_looks("user_a")[0].look_id == look.look_id
    assert favorites_repo.list_looks("user_b") == []
```

- [ ] **Step 2: Run the new test and verify the first failure**

Run:

```bash
cd backend
python -m pytest tests/test_favorites_repository.py -q
```

Expected: FAIL because `app.schemas.favorites` or `InMemoryFavoritesRepository` does not exist.

- [ ] **Step 3: Add favorite and saved-look schemas**

Create `backend/app/schemas/favorites.py`:

```python
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.schemas.domain import OutfitCandidate, ProductCandidate
from app.schemas.quality import ImageQualityReport, RecommendationReport


class FavoriteProductCreate(ProductCandidate):
    source_task_id: str | None = None


class FavoriteProduct(ProductCandidate):
    favorite_id: str
    user_id: str
    source_task_id: str | None = None
    created_at: datetime


class SavedLook(BaseModel):
    look_id: str
    user_id: str
    source_task_id: str | None = None
    outfit: OutfitCandidate | None = None
    recommendation_report: RecommendationReport
    try_on_image_url: str | None = None
    image_quality_report: ImageQualityReport | None = None
    created_at: datetime
```

- [ ] **Step 4: Extend local repositories**

Modify `backend/app/providers/persistence.py` with these signatures and local implementations. Keep existing task methods and messages, but change `create` to accept `user_id` and add `owner_id`.

```python
class TaskRepository(Protocol):
    def create(self, task_id: str, request: StyleTaskRequest, user_id: str | None = None) -> StyleTaskView:
        ...

    def update_status(self, task_id: str, status: TaskStatus, message: str, progress: int) -> StyleTaskView:
        ...

    def complete(self, task_id: str, result: StyleTaskResult) -> StyleTaskView:
        ...

    def fail(self, task_id: str, message: str) -> StyleTaskView:
        ...

    def get(self, task_id: str) -> StyleTaskView:
        ...

    def owner_id(self, task_id: str) -> str | None:
        ...


class WardrobeRepository(Protocol):
    def list_for_user(self, owner_id: str | None = None) -> list[WardrobeItem]:
        ...

    def save(self, item: WardrobeItem) -> WardrobeItem:
        ...

    def products_for_ids(self, item_ids: list[str]) -> list[ProductCandidate]:
        ...


class FavoritesRepository(Protocol):
    def save_product(self, user_id: str, product: FavoriteProductCreate) -> FavoriteProduct:
        ...

    def list_products(self, user_id: str) -> list[FavoriteProduct]:
        ...

    def delete_product(self, user_id: str, favorite_id: str) -> bool:
        ...

    def save_look(self, user_id: str, task: StyleTaskView) -> SavedLook:
        ...

    def list_looks(self, user_id: str) -> list[SavedLook]:
        ...
```

Add these imports near the top of `persistence.py`:

```python
from uuid import uuid4

from app.schemas.favorites import FavoriteProduct, FavoriteProductCreate, SavedLook
```

Update `InMemoryTaskRepository`:

```python
@dataclass
class InMemoryTaskRepository:
    tasks: dict[str, StyleTaskView] = field(default_factory=dict)
    task_owner_ids: dict[str, str | None] = field(default_factory=dict)

    def create(self, task_id: str, request: StyleTaskRequest, user_id: str | None = None) -> StyleTaskView:
        task = StyleTaskView(
            task_id=task_id,
            status=TaskStatus.created,
            progress=2,
            message="Task created",
            request=request,
            created_at=now_utc(),
            updated_at=now_utc(),
        )
        self.tasks[task_id] = task
        self.task_owner_ids[task_id] = user_id
        return task

    def owner_id(self, task_id: str) -> str | None:
        self.get(task_id)
        return self.task_owner_ids.get(task_id)
```

Add `InMemoryFavoritesRepository` at the end of `persistence.py`:

```python
@dataclass
class InMemoryFavoritesRepository:
    favorite_products: dict[str, FavoriteProduct] = field(default_factory=dict)
    saved_looks: dict[str, SavedLook] = field(default_factory=dict)

    def save_product(self, user_id: str, product: FavoriteProductCreate) -> FavoriteProduct:
        for favorite in self.favorite_products.values():
            if (
                favorite.user_id == user_id
                and favorite.product_id == product.product_id
                and favorite.marketplace == product.marketplace
            ):
                return favorite
        created = FavoriteProduct(
            **product.model_dump(),
            favorite_id=f"favorite_{uuid4().hex[:16]}",
            user_id=user_id,
            created_at=now_utc(),
        )
        self.favorite_products[created.favorite_id] = created
        return created

    def list_products(self, user_id: str) -> list[FavoriteProduct]:
        return sorted(
            [favorite for favorite in self.favorite_products.values() if favorite.user_id == user_id],
            key=lambda favorite: favorite.created_at,
            reverse=True,
        )

    def delete_product(self, user_id: str, favorite_id: str) -> bool:
        favorite = self.favorite_products.get(favorite_id)
        if favorite is None or favorite.user_id != user_id:
            return False
        del self.favorite_products[favorite_id]
        return True

    def save_look(self, user_id: str, task: StyleTaskView) -> SavedLook:
        if task.result is None or task.result.recommendation_report is None:
            raise ValueError("Task has no recommendation report to save")
        for look in self.saved_looks.values():
            if look.user_id == user_id and look.source_task_id == task.task_id:
                return look
        created = SavedLook(
            look_id=f"look_{uuid4().hex[:16]}",
            user_id=user_id,
            source_task_id=task.task_id,
            outfit=task.result.outfit,
            recommendation_report=task.result.recommendation_report,
            try_on_image_url=task.result.try_on_image_url,
            image_quality_report=task.result.image_quality_report,
            created_at=now_utc(),
        )
        self.saved_looks[created.look_id] = created
        return created

    def list_looks(self, user_id: str) -> list[SavedLook]:
        return sorted(
            [look for look in self.saved_looks.values() if look.user_id == user_id],
            key=lambda look: look.created_at,
            reverse=True,
        )
```

- [ ] **Step 5: Thread favorites through `TaskService`**

Modify `backend/app/services/task_service.py` imports:

```python
from app.providers.persistence import (
    FavoritesRepository,
    InMemoryFavoritesRepository,
    InMemoryTaskRepository,
    InMemoryWardrobeRepository,
    TaskRepository,
    WardrobeRepository,
)
from app.schemas.favorites import FavoriteProduct, FavoriteProductCreate, SavedLook
```

Modify the dataclass and methods:

```python
@dataclass
class TaskService:
    repository: TaskRepository
    wardrobe_repository: WardrobeRepository
    favorites_repository: FavoritesRepository
    graph: StyleAgentGraph
    tracer: InMemoryTraceRecorder

    def create_task(self, request: StyleTaskRequest, user_id: str | None = None) -> StyleTaskView:
        task_id = f"task_{uuid4().hex[:16]}"
        return self.repository.create(task_id, request, user_id=user_id)

    def task_owner_id(self, task_id: str) -> str | None:
        return self.repository.owner_id(task_id)

    def save_favorite_product(self, user_id: str, product: FavoriteProductCreate) -> FavoriteProduct:
        return self.favorites_repository.save_product(user_id, product)

    def list_favorite_products(self, user_id: str) -> list[FavoriteProduct]:
        return self.favorites_repository.list_products(user_id)

    def delete_favorite_product(self, user_id: str, favorite_id: str) -> bool:
        return self.favorites_repository.delete_product(user_id, favorite_id)

    def save_look(self, user_id: str, task_id: str) -> SavedLook:
        task = self.repository.get(task_id)
        owner_id = self.repository.owner_id(task_id)
        if owner_id != user_id:
            raise PermissionError("Task not found")
        if task.result is None or task.result.outfit is None or task.result.recommendation_report is None:
            raise ValueError("Task has no completed look to save")
        return self.favorites_repository.save_look(user_id, task)

    def list_saved_looks(self, user_id: str) -> list[SavedLook]:
        return self.favorites_repository.list_looks(user_id)
```

Modify `create_task_service`:

```python
def create_task_service(
    graph: StyleAgentGraph,
    tracer: InMemoryTraceRecorder,
    wardrobe_repository: WardrobeRepository | None = None,
    favorites_repository: FavoritesRepository | None = None,
    repository: TaskRepository | None = None,
) -> TaskService:
    return TaskService(
        repository=repository or InMemoryTaskRepository(),
        wardrobe_repository=wardrobe_repository or InMemoryWardrobeRepository(),
        favorites_repository=favorites_repository or InMemoryFavoritesRepository(),
        graph=graph,
        tracer=tracer,
    )
```

- [ ] **Step 6: Run local repository tests**

Run:

```bash
cd backend
python -m pytest tests/test_favorites_repository.py -q
```

Expected: PASS.

- [ ] **Step 7: Run existing auth tests for regressions**

Run:

```bash
cd backend
python -m pytest tests/test_auth.py -q
```

Expected: PASS.

- [ ] **Step 8: Commit Task 1**

```bash
git add backend/app/schemas/favorites.py backend/app/providers/persistence.py backend/app/services/task_service.py backend/tests/test_favorites_repository.py
git commit -m "feat: add favorite persistence boundary"
```

---

### Task 2: SQL Migration for Production Tables

**Files:**
- Modify: `backend/migrations/001_initial.sql`
- Test: `backend/tests/test_migration_sql.py`

- [ ] **Step 1: Write migration structure test**

Create `backend/tests/test_migration_sql.py`:

```python
from __future__ import annotations

from pathlib import Path


def migration_sql() -> str:
    return Path("migrations/001_initial.sql").read_text(encoding="utf-8")


def test_initial_migration_defines_auth_and_favorite_tables() -> None:
    sql = migration_sql()

    assert "CREATE TABLE IF NOT EXISTS auth_users" in sql
    assert "CREATE TABLE IF NOT EXISTS auth_sessions" in sql
    assert "CREATE TABLE IF NOT EXISTS favorite_products" in sql
    assert "idx_favorite_products_user_created" in sql
    assert "uq_favorite_products_user_product_marketplace" in sql
    assert "idx_saved_looks_unique_user_task" in sql


def test_initial_migration_links_user_owned_tables() -> None:
    sql = migration_sql()

    assert "auth_sessions_user_id_fkey" in sql
    assert "style_tasks_user_id_fkey" in sql
    assert "saved_looks_user_id_fkey" in sql
```

- [ ] **Step 2: Run migration test and verify failure**

Run:

```bash
cd backend
python -m pytest tests/test_migration_sql.py -q
```

Expected: FAIL because the auth and favorite tables are absent.

- [ ] **Step 3: Extend `001_initial.sql`**

Append this SQL after `CREATE EXTENSION IF NOT EXISTS vector;` and before dependent tables where possible. If appending after existing tables is simpler, use the `DO $$` blocks exactly as shown so repeated migration application is safe.

```sql
CREATE TABLE IF NOT EXISTS auth_users (
  user_id TEXT PRIMARY KEY,
  google_sub TEXT UNIQUE NOT NULL,
  email TEXT UNIQUE NOT NULL,
  name TEXT NOT NULL,
  avatar_url TEXT,
  provider TEXT NOT NULL DEFAULT 'google',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_auth_users_email
  ON auth_users (email);

CREATE TABLE IF NOT EXISTS auth_sessions (
  session_id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  token_hash TEXT UNIQUE NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  expires_at TIMESTAMPTZ NOT NULL
);

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'auth_sessions_user_id_fkey'
  ) THEN
    ALTER TABLE auth_sessions
      ADD CONSTRAINT auth_sessions_user_id_fkey
      FOREIGN KEY (user_id) REFERENCES auth_users(user_id) ON DELETE CASCADE;
  END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_auth_sessions_token_hash
  ON auth_sessions (token_hash);

CREATE INDEX IF NOT EXISTS idx_auth_sessions_user_expires
  ON auth_sessions (user_id, expires_at DESC);
```

Add these constraint blocks after `style_tasks` and `saved_looks` exist:

```sql
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'style_tasks_user_id_fkey'
  ) THEN
    ALTER TABLE style_tasks
      ADD CONSTRAINT style_tasks_user_id_fkey
      FOREIGN KEY (user_id) REFERENCES auth_users(user_id) ON DELETE SET NULL;
  END IF;
END $$;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'saved_looks_user_id_fkey'
  ) THEN
    ALTER TABLE saved_looks
      ADD CONSTRAINT saved_looks_user_id_fkey
      FOREIGN KEY (user_id) REFERENCES auth_users(user_id) ON DELETE CASCADE;
  END IF;
END $$;

CREATE UNIQUE INDEX IF NOT EXISTS idx_saved_looks_unique_user_task
  ON saved_looks (user_id, source_task_id)
  WHERE source_task_id IS NOT NULL;
```

Add the favorite table after `product_snapshots` or after `saved_looks`:

```sql
CREATE TABLE IF NOT EXISTS favorite_products (
  favorite_id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL REFERENCES auth_users(user_id) ON DELETE CASCADE,
  product_id TEXT NOT NULL,
  marketplace TEXT NOT NULL,
  category TEXT NOT NULL,
  title TEXT NOT NULL,
  price NUMERIC NOT NULL DEFAULT 0,
  price_text TEXT,
  image_url TEXT NOT NULL,
  product_url TEXT NOT NULL,
  shop_name TEXT,
  sizes TEXT[] NOT NULL DEFAULT '{}',
  colors TEXT[] NOT NULL DEFAULT '{}',
  style_tags TEXT[] NOT NULL DEFAULT '{}',
  fit_tags TEXT[] NOT NULL DEFAULT '{}',
  source_reliability NUMERIC NOT NULL DEFAULT 0,
  score NUMERIC NOT NULL DEFAULT 0,
  risk_flags TEXT[] NOT NULL DEFAULT '{}',
  raw JSONB NOT NULL DEFAULT '{}',
  source_task_id TEXT REFERENCES style_tasks(task_id) ON DELETE SET NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_favorite_products_user_created
  ON favorite_products (user_id, created_at DESC);

CREATE UNIQUE INDEX IF NOT EXISTS uq_favorite_products_user_product_marketplace
  ON favorite_products (user_id, product_id, marketplace);
```

- [ ] **Step 4: Run migration structure tests**

Run:

```bash
cd backend
python -m pytest tests/test_migration_sql.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit Task 2**

```bash
git add backend/migrations/001_initial.sql backend/tests/test_migration_sql.py
git commit -m "feat: add postgres persistence schema"
```

---

### Task 3: Postgres Repository Implementations

**Files:**
- Replace: `backend/app/providers/postgres.py`
- Test: `backend/tests/test_postgres_persistence.py`

- [ ] **Step 1: Write Postgres integration tests**

Create `backend/tests/test_postgres_persistence.py`:

```python
from __future__ import annotations

import os
from pathlib import Path
from uuid import uuid4

import psycopg
import pytest

from app.providers.auth import GoogleProfile
from app.providers.postgres import (
    PostgresAuthStore,
    PostgresDatabase,
    PostgresFavoritesRepository,
    PostgresTaskRepository,
    PostgresTraceRecorder,
    PostgresWardrobeRepository,
)
from app.schemas.domain import Budget, Marketplace, ProductCandidate, ProductCategory, Scene, StyleTaskRequest, TaskStatus, WardrobeItem
from app.schemas.favorites import FavoriteProductCreate
from app.schemas.quality import GateStatus, QualityGateReport, RecommendationReport
from app.schemas.results import StyleTaskResult


TEST_DSN = os.getenv("STYLE_BACKEND_TEST_POSTGRES_DSN")

pytestmark = pytest.mark.skipif(not TEST_DSN, reason="STYLE_BACKEND_TEST_POSTGRES_DSN is not configured")


@pytest.fixture()
def db() -> PostgresDatabase:
    assert TEST_DSN is not None
    database = PostgresDatabase(TEST_DSN)
    with database.connect() as connection:
        connection.execute(Path("migrations/001_initial.sql").read_text(encoding="utf-8"))
        connection.execute("TRUNCATE favorite_products, saved_looks, trace_events, wardrobe_items, style_tasks, auth_sessions, auth_users RESTART IDENTITY CASCADE")
    return database


def google_profile(email: str = "Style.User@Example.com", sub: str | None = None) -> GoogleProfile:
    return GoogleProfile(
        sub=sub or f"google-sub-{uuid4().hex}",
        email=email,
        email_verified=True,
        name="Style User",
        avatar_url="https://example.com/avatar.png",
    )


def request() -> StyleTaskRequest:
    return StyleTaskRequest(
        photo_url="https://example.com/person.jpg",
        photo_object_key="uploads/person.jpg",
        scene=Scene.daily,
        budget=Budget(min=300, max=800),
        marketplaces=[Marketplace.tmall],
    )


def product(product_id: str = "tmall_100") -> ProductCandidate:
    return ProductCandidate(
        product_id=product_id,
        marketplace=Marketplace.tmall,
        category=ProductCategory.top,
        title="White shirt",
        price=199,
        price_text="CNY 199",
        image_url="https://example.com/shirt.jpg",
        product_url="https://detail.tmall.com/item.htm?id=100",
        shop_name="Example Shop",
        sizes=["M"],
        colors=["white"],
        style_tags=["clean"],
        fit_tags=["regular"],
        source_reliability=0.91,
        score=0.88,
        raw={"source": "test"},
    )


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


def test_postgres_auth_store_persists_users_sessions_and_logout(db: PostgresDatabase) -> None:
    store = PostgresAuthStore(db, session_max_age_days=30)
    user = store.upsert_google_user(google_profile())
    session = store.create_session(user.user_id)

    reloaded = PostgresAuthStore(db, session_max_age_days=30)
    stored_user = reloaded.get_user_by_token(session.token)
    assert stored_user is not None
    assert stored_user.user_id == user.user_id
    assert stored_user.email == "style.user@example.com"

    reloaded.destroy_session(session.token)
    assert reloaded.get_user_by_token(session.token) is None


def test_postgres_task_trace_and_wardrobe_repositories_round_trip(db: PostgresDatabase) -> None:
    auth = PostgresAuthStore(db, session_max_age_days=30)
    user = auth.upsert_google_user(google_profile())
    tasks = PostgresTaskRepository(db)
    traces = PostgresTraceRecorder(db)
    wardrobe = PostgresWardrobeRepository(db)

    task = tasks.create("task_1", request(), user_id=user.user_id)
    tasks.update_status(task.task_id, TaskStatus.scouting_products, "searching", 40)
    result = StyleTaskResult(task_id=task.task_id, status=TaskStatus.failed, user_message="failed")
    tasks.complete(task.task_id, result)
    traces.record(task.task_id, "Node", "event", {"ok": True})
    wardrobe.save(
        WardrobeItem(
            item_id="wardrobe_1",
            owner_id=user.user_id,
            category=ProductCategory.top,
            title="Owned shirt",
            image_url="https://example.com/owned.jpg",
        )
    )

    reloaded = tasks.get(task.task_id)
    assert tasks.owner_id(task.task_id) == user.user_id
    assert reloaded.status == TaskStatus.failed
    assert reloaded.result is not None
    assert traces.by_task(task.task_id)[0]["payload"] == {"ok": True}
    assert wardrobe.list_for_user(user.user_id)[0].title == "Owned shirt"
    assert wardrobe.products_for_ids(["wardrobe_1"])[0].marketplace == Marketplace.owned


def test_postgres_favorites_and_saved_looks_are_user_scoped_and_idempotent(db: PostgresDatabase) -> None:
    auth = PostgresAuthStore(db, session_max_age_days=30)
    user = auth.upsert_google_user(google_profile(email="first@example.com"))
    other = auth.upsert_google_user(google_profile(email="second@example.com"))
    tasks = PostgresTaskRepository(db)
    favorites = PostgresFavoritesRepository(db)

    task = tasks.create("task_1", request(), user_id=user.user_id)
    result = StyleTaskResult(
        task_id=task.task_id,
        status=TaskStatus.partial_succeeded,
        outfit=None,
        recommendation_report=recommendation_report(),
        user_message="partial",
    )
    tasks.complete(task.task_id, result)

    first = favorites.save_product(user.user_id, FavoriteProductCreate(**product().model_dump(), source_task_id=task.task_id))
    duplicate = favorites.save_product(user.user_id, FavoriteProductCreate(**product().model_dump(), source_task_id=task.task_id))
    other_user = favorites.save_product(other.user_id, FavoriteProductCreate(**product().model_dump(), source_task_id=None))
    look = favorites.save_look(user.user_id, tasks.get(task.task_id))
    duplicate_look = favorites.save_look(user.user_id, tasks.get(task.task_id))

    assert duplicate.favorite_id == first.favorite_id
    assert other_user.favorite_id != first.favorite_id
    assert [item.favorite_id for item in favorites.list_products(user.user_id)] == [first.favorite_id]
    assert favorites.delete_product(user.user_id, other_user.favorite_id) is False
    assert duplicate_look.look_id == look.look_id
    assert favorites.list_looks(user.user_id)[0].look_id == look.look_id
```

- [ ] **Step 2: Run Postgres tests and verify first failure**

With a test database:

```bash
cd backend
$env:STYLE_BACKEND_TEST_POSTGRES_DSN="postgresql://postgres:postgres@127.0.0.1:5432/clothes_test"
python -m pytest tests/test_postgres_persistence.py -q
```

Expected with DSN: FAIL because the Postgres repository classes are not implemented. Expected without DSN: SKIPPED.

- [ ] **Step 3: Replace `backend/app/providers/postgres.py`**

Use this structure. Keep code synchronous because existing repository interfaces are synchronous.

```python
from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from app.providers.auth import GoogleProfile
from app.providers.persistence import now_utc
from app.schemas.auth import AuthSession, AuthSessionRecord, AuthUserRecord, PublicUser
from app.schemas.domain import Marketplace, ProductCandidate, StyleTaskRequest, TaskStatus, WardrobeItem
from app.schemas.favorites import FavoriteProduct, FavoriteProductCreate, SavedLook
from app.schemas.results import StyleTaskResult, StyleTaskView


class PostgresDatabase:
    def __init__(self, dsn: str) -> None:
        self.dsn = dsn

    def connect(self) -> psycopg.Connection[dict[str, Any]]:
        return psycopg.connect(self.dsn, row_factory=dict_row)

    def check_connection(self) -> None:
        with self.connect() as connection:
            connection.execute("SELECT 1")
```

Add row helpers:

```python
def _json(model: Any) -> Jsonb:
    if hasattr(model, "model_dump"):
        return Jsonb(model.model_dump(mode="json"))
    return Jsonb(model)


def _task_from_row(row: dict[str, Any]) -> StyleTaskView:
    return StyleTaskView(
        task_id=row["task_id"],
        status=TaskStatus(row["status"]),
        progress=row["progress"],
        message=row["message"],
        request=StyleTaskRequest.model_validate(row["request"]),
        result=StyleTaskResult.model_validate(row["result"]) if row["result"] is not None else None,
        error=row["error"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )
```

Implement `PostgresAuthStore` with the same public methods as `AuthStore`:

```python
class PostgresAuthStore:
    def __init__(self, database: PostgresDatabase, session_max_age_days: int) -> None:
        self.database = database
        self.session_max_age_days = session_max_age_days

    def upsert_google_user(self, profile: GoogleProfile) -> AuthUserRecord:
        if not profile.email_verified:
            raise ValueError("Google profile email must be verified")
        email = profile.email.strip().lower()
        now = self._now()
        with self.database.connect() as connection:
            existing = connection.execute(
                """
                SELECT * FROM auth_users
                WHERE google_sub = %(google_sub)s OR email = %(email)s
                ORDER BY CASE WHEN google_sub = %(google_sub)s THEN 0 ELSE 1 END
                """,
                {"google_sub": profile.sub, "email": email},
            ).fetchall()
            if len({row["user_id"] for row in existing}) > 1:
                raise ValueError("Google profile email belongs to another user")
            if existing:
                user_id = existing[0]["user_id"]
                row = connection.execute(
                    """
                    UPDATE auth_users
                    SET google_sub = %(google_sub)s,
                        email = %(email)s,
                        name = %(name)s,
                        avatar_url = %(avatar_url)s,
                        updated_at = %(updated_at)s
                    WHERE user_id = %(user_id)s
                    RETURNING *
                    """,
                    {
                        "user_id": user_id,
                        "google_sub": profile.sub,
                        "email": email,
                        "name": profile.name or existing[0]["name"],
                        "avatar_url": profile.avatar_url or existing[0]["avatar_url"],
                        "updated_at": now,
                    },
                ).fetchone()
            else:
                row = connection.execute(
                    """
                    INSERT INTO auth_users (user_id, google_sub, email, name, avatar_url, provider, created_at, updated_at)
                    VALUES (%(user_id)s, %(google_sub)s, %(email)s, %(name)s, %(avatar_url)s, 'google', %(created_at)s, %(updated_at)s)
                    RETURNING *
                    """,
                    {
                        "user_id": f"user_{uuid4().hex[:16]}",
                        "google_sub": profile.sub,
                        "email": email,
                        "name": profile.name or email.split("@")[0] or "Google User",
                        "avatar_url": profile.avatar_url,
                        "created_at": now,
                        "updated_at": now,
                    },
                ).fetchone()
            assert row is not None
            return AuthUserRecord.model_validate(row)
```

Add the remaining auth methods:

```python
    def create_session(self, user_id: str) -> AuthSession:
        self._prune_expired_sessions()
        now = self._now()
        expires_at = now + timedelta(days=self.session_max_age_days)
        token = secrets.token_urlsafe(32)
        with self.database.connect() as connection:
            user = connection.execute("SELECT user_id FROM auth_users WHERE user_id = %s", (user_id,)).fetchone()
            if user is None:
                raise ValueError(f"Unknown auth user: {user_id}")
            connection.execute(
                """
                INSERT INTO auth_sessions (session_id, user_id, token_hash, created_at, expires_at)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (f"session_{uuid4().hex[:16]}", user_id, self._hash_token(token), now, expires_at),
            )
        return AuthSession(token=token, expires_at=expires_at)

    def get_user_by_token(self, token: str | None) -> PublicUser | None:
        if not token:
            return None
        self._prune_expired_sessions()
        token_hash = self._hash_token(token)
        with self.database.connect() as connection:
            row = connection.execute(
                """
                SELECT u.user_id, u.email, u.name, u.avatar_url, u.provider
                FROM auth_sessions s
                JOIN auth_users u ON u.user_id = s.user_id
                WHERE s.token_hash = %s AND s.expires_at > %s
                """,
                (token_hash, self._now()),
            ).fetchone()
        return PublicUser.model_validate(row) if row else None

    def destroy_session(self, token: str | None) -> None:
        if not token:
            return
        with self.database.connect() as connection:
            connection.execute("DELETE FROM auth_sessions WHERE token_hash = %s", (self._hash_token(token),))

    def _prune_expired_sessions(self) -> None:
        with self.database.connect() as connection:
            connection.execute("DELETE FROM auth_sessions WHERE expires_at <= %s", (self._now(),))

    @staticmethod
    def _hash_token(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    @staticmethod
    def _token_hash_matches(session: AuthSessionRecord, token_hash: str) -> bool:
        return hmac.compare_digest(session.token_hash, token_hash)

    @staticmethod
    def _now() -> datetime:
        return datetime.now(UTC)
```

Add these repository classes after `PostgresAuthStore`:

```python
class PostgresTaskRepository:
    def __init__(self, database: PostgresDatabase) -> None:
        self.database = database

    def create(self, task_id: str, request: StyleTaskRequest, user_id: str | None = None) -> StyleTaskView:
        now = now_utc()
        with self.database.connect() as connection:
            row = connection.execute(
                """
                INSERT INTO style_tasks (task_id, user_id, status, progress, message, request, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING *
                """,
                (task_id, user_id, TaskStatus.created.value, 2, "Task created", _json(request), now, now),
            ).fetchone()
        assert row is not None
        return _task_from_row(row)

    def update_status(self, task_id: str, status: TaskStatus, message: str, progress: int) -> StyleTaskView:
        with self.database.connect() as connection:
            row = connection.execute(
                """
                UPDATE style_tasks
                SET status = %s, message = %s, progress = %s, updated_at = %s
                WHERE task_id = %s
                RETURNING *
                """,
                (status.value, message, progress, now_utc(), task_id),
            ).fetchone()
        if row is None:
            raise KeyError(f"Task not found: {task_id}")
        return _task_from_row(row)

    def complete(self, task_id: str, result: StyleTaskResult) -> StyleTaskView:
        task = self.get(task_id)
        status = result.status
        progress = 100 if status in {TaskStatus.succeeded, TaskStatus.partial_succeeded} else task.progress
        message = result.user_message or ("Styling complete" if status == TaskStatus.succeeded else "Recommendation complete")
        with self.database.connect() as connection:
            row = connection.execute(
                """
                UPDATE style_tasks
                SET status = %s, progress = %s, message = %s, result = %s, error = NULL, updated_at = %s
                WHERE task_id = %s
                RETURNING *
                """,
                (status.value, progress, message, _json(result), now_utc(), task_id),
            ).fetchone()
        if row is None:
            raise KeyError(f"Task not found: {task_id}")
        return _task_from_row(row)

    def fail(self, task_id: str, message: str) -> StyleTaskView:
        with self.database.connect() as connection:
            row = connection.execute(
                """
                UPDATE style_tasks
                SET status = %s, message = %s, progress = 100, error = %s, updated_at = %s
                WHERE task_id = %s
                RETURNING *
                """,
                (TaskStatus.failed.value, message, message, now_utc(), task_id),
            ).fetchone()
        if row is None:
            raise KeyError(f"Task not found: {task_id}")
        return _task_from_row(row)

    def get(self, task_id: str) -> StyleTaskView:
        with self.database.connect() as connection:
            row = connection.execute("SELECT * FROM style_tasks WHERE task_id = %s", (task_id,)).fetchone()
        if row is None:
            raise KeyError(f"Task not found: {task_id}")
        return _task_from_row(row)

    def owner_id(self, task_id: str) -> str | None:
        with self.database.connect() as connection:
            row = connection.execute("SELECT user_id FROM style_tasks WHERE task_id = %s", (task_id,)).fetchone()
        if row is None:
            raise KeyError(f"Task not found: {task_id}")
        return row["user_id"]


class PostgresTraceRecorder:
    def __init__(self, database: PostgresDatabase) -> None:
        self.database = database

    def record(self, task_id: str, node: str, event: str, payload: dict[str, Any]) -> None:
        with self.database.connect() as connection:
            connection.execute(
                "INSERT INTO trace_events (task_id, node, event, payload) VALUES (%s, %s, %s, %s)",
                (task_id, node, event, Jsonb(payload)),
            )

    def by_task(self, task_id: str) -> list[dict[str, Any]]:
        with self.database.connect() as connection:
            rows = connection.execute(
                """
                SELECT created_at, task_id, node, event, payload
                FROM trace_events
                WHERE task_id = %s
                ORDER BY created_at, event_id
                """,
                (task_id,),
            ).fetchall()
        return [
            {
                "timestamp": row["created_at"].isoformat(),
                "task_id": row["task_id"],
                "node": row["node"],
                "event": row["event"],
                "payload": row["payload"],
            }
            for row in rows
        ]


class PostgresWardrobeRepository:
    def __init__(self, database: PostgresDatabase) -> None:
        self.database = database

    def list_for_user(self, owner_id: str | None = None) -> list[WardrobeItem]:
        with self.database.connect() as connection:
            if owner_id is None:
                rows = connection.execute("SELECT * FROM wardrobe_items ORDER BY created_at DESC").fetchall()
            else:
                rows = connection.execute(
                    "SELECT * FROM wardrobe_items WHERE owner_id = %s ORDER BY created_at DESC",
                    (owner_id,),
                ).fetchall()
        return [WardrobeItem.model_validate(row) for row in rows]

    def save(self, item: WardrobeItem) -> WardrobeItem:
        now = now_utc()
        with self.database.connect() as connection:
            row = connection.execute(
                """
                INSERT INTO wardrobe_items (
                  item_id, owner_id, category, title, image_url, colors, style_tags, fit_tags, notes, created_at, updated_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (item_id) DO UPDATE
                SET owner_id = EXCLUDED.owner_id,
                    category = EXCLUDED.category,
                    title = EXCLUDED.title,
                    image_url = EXCLUDED.image_url,
                    colors = EXCLUDED.colors,
                    style_tags = EXCLUDED.style_tags,
                    fit_tags = EXCLUDED.fit_tags,
                    notes = EXCLUDED.notes,
                    updated_at = EXCLUDED.updated_at
                RETURNING *
                """,
                (
                    item.item_id,
                    item.owner_id,
                    item.category.value,
                    item.title,
                    str(item.image_url),
                    item.colors,
                    item.style_tags,
                    item.fit_tags,
                    item.notes,
                    now,
                    now,
                ),
            ).fetchone()
        assert row is not None
        return WardrobeItem.model_validate(row)

    def products_for_ids(self, item_ids: list[str]) -> list[ProductCandidate]:
        if not item_ids:
            return []
        with self.database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM wardrobe_items WHERE item_id = ANY(%s)",
                (item_ids,),
            ).fetchall()
        products: list[ProductCandidate] = []
        for row in rows:
            item = WardrobeItem.model_validate(row)
            products.append(
                ProductCandidate(
                    product_id=item.item_id,
                    marketplace=Marketplace.owned,
                    category=item.category,
                    title=item.title,
                    price=0,
                    price_text="Owned wardrobe",
                    image_url=str(item.image_url),
                    product_url=f"owned://wardrobe/{item.item_id}",
                    colors=item.colors,
                    style_tags=item.style_tags,
                    fit_tags=item.fit_tags,
                    source_reliability=0.94,
                    score=0.92,
                    raw={"notes": item.notes},
                )
            )
        return products


class PostgresFavoritesRepository:
    def __init__(self, database: PostgresDatabase) -> None:
        self.database = database

    def save_product(self, user_id: str, product: FavoriteProductCreate) -> FavoriteProduct:
        with self.database.connect() as connection:
            row = connection.execute(
                """
                INSERT INTO favorite_products (
                  favorite_id, user_id, product_id, marketplace, category, title, price, price_text,
                  image_url, product_url, shop_name, sizes, colors, style_tags, fit_tags,
                  source_reliability, score, risk_flags, raw, source_task_id
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (user_id, product_id, marketplace) DO UPDATE
                SET source_task_id = COALESCE(EXCLUDED.source_task_id, favorite_products.source_task_id)
                RETURNING *
                """,
                (
                    f"favorite_{uuid4().hex[:16]}",
                    user_id,
                    product.product_id,
                    product.marketplace.value,
                    product.category.value,
                    product.title,
                    product.price,
                    product.price_text,
                    product.image_url,
                    product.product_url,
                    product.shop_name,
                    product.sizes,
                    product.colors,
                    product.style_tags,
                    product.fit_tags,
                    product.source_reliability,
                    product.score,
                    product.risk_flags,
                    Jsonb(product.raw),
                    product.source_task_id,
                ),
            ).fetchone()
        assert row is not None
        return FavoriteProduct.model_validate(row)

    def list_products(self, user_id: str) -> list[FavoriteProduct]:
        with self.database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM favorite_products WHERE user_id = %s ORDER BY created_at DESC",
                (user_id,),
            ).fetchall()
        return [FavoriteProduct.model_validate(row) for row in rows]

    def delete_product(self, user_id: str, favorite_id: str) -> bool:
        with self.database.connect() as connection:
            cursor = connection.execute(
                "DELETE FROM favorite_products WHERE user_id = %s AND favorite_id = %s",
                (user_id, favorite_id),
            )
            return cursor.rowcount > 0

    def save_look(self, user_id: str, task: StyleTaskView) -> SavedLook:
        if task.result is None or task.result.recommendation_report is None:
            raise ValueError("Task has no recommendation report to save")
        with self.database.connect() as connection:
            row = connection.execute(
                """
                INSERT INTO saved_looks (
                  look_id, user_id, source_task_id, outfit, recommendation_report,
                  try_on_image_url, image_quality_report
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (user_id, source_task_id) WHERE source_task_id IS NOT NULL DO UPDATE
                SET source_task_id = EXCLUDED.source_task_id
                RETURNING *
                """,
                (
                    f"look_{uuid4().hex[:16]}",
                    user_id,
                    task.task_id,
                    _json(task.result.outfit) if task.result.outfit is not None else None,
                    _json(task.result.recommendation_report),
                    task.result.try_on_image_url,
                    _json(task.result.image_quality_report) if task.result.image_quality_report is not None else None,
                ),
            ).fetchone()
        assert row is not None
        return SavedLook.model_validate(row)

    def list_looks(self, user_id: str) -> list[SavedLook]:
        with self.database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM saved_looks WHERE user_id = %s ORDER BY created_at DESC",
                (user_id,),
            ).fetchall()
        return [SavedLook.model_validate(row) for row in rows]
```

- [ ] **Step 4: Run Postgres tests**

With a test database:

```bash
cd backend
$env:STYLE_BACKEND_TEST_POSTGRES_DSN="postgresql://postgres:postgres@127.0.0.1:5432/clothes_test"
python -m pytest tests/test_postgres_persistence.py -q
```

Expected with DSN: PASS. Expected without DSN: SKIPPED.

- [ ] **Step 5: Run local repository tests again**

Run:

```bash
cd backend
python -m pytest tests/test_favorites_repository.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit Task 3**

```bash
git add backend/app/providers/postgres.py backend/tests/test_postgres_persistence.py
git commit -m "feat: persist backend repositories in postgres"
```

---

### Task 4: Container Wiring for Postgres Mode

**Files:**
- Modify: `backend/app/services/container.py`
- Test: `backend/tests/test_container_persistence.py`

- [ ] **Step 1: Write container selection tests**

Create `backend/tests/test_container_persistence.py`:

```python
from __future__ import annotations

from app.config import get_settings
from app.providers.persistence import InMemoryFavoritesRepository, InMemoryTaskRepository, InMemoryWardrobeRepository
from app.providers.postgres import (
    PostgresAuthStore,
    PostgresDatabase,
    PostgresFavoritesRepository,
    PostgresTaskRepository,
    PostgresTraceRecorder,
    PostgresWardrobeRepository,
)
from app.services.container import AppContainer, get_container


def test_container_uses_local_repositories_without_postgres_dsn(monkeypatch, tmp_path) -> None:
    get_container.cache_clear()
    get_settings.cache_clear()
    monkeypatch.delenv("STYLE_BACKEND_POSTGRES_DSN", raising=False)
    monkeypatch.setenv("STYLE_BACKEND_AUTH_STORE_PATH", str(tmp_path / "auth.json"))

    container = AppContainer()

    assert isinstance(container.task_service.repository, InMemoryTaskRepository)
    assert isinstance(container.task_service.wardrobe_repository, InMemoryWardrobeRepository)
    assert isinstance(container.task_service.favorites_repository, InMemoryFavoritesRepository)


def test_container_uses_postgres_repositories_when_dsn_is_configured(monkeypatch, tmp_path) -> None:
    get_container.cache_clear()
    get_settings.cache_clear()
    monkeypatch.setenv("STYLE_BACKEND_POSTGRES_DSN", "postgresql://example/test")
    monkeypatch.setenv("STYLE_BACKEND_AUTH_STORE_PATH", str(tmp_path / "auth.json"))
    monkeypatch.setattr(PostgresDatabase, "check_connection", lambda self: None)

    container = AppContainer()

    assert isinstance(container.auth_store, PostgresAuthStore)
    assert isinstance(container.tracer, PostgresTraceRecorder)
    assert isinstance(container.task_service.repository, PostgresTaskRepository)
    assert isinstance(container.task_service.wardrobe_repository, PostgresWardrobeRepository)
    assert isinstance(container.task_service.favorites_repository, PostgresFavoritesRepository)
```

- [ ] **Step 2: Run container tests and verify failure**

Run:

```bash
cd backend
python -m pytest tests/test_container_persistence.py -q
```

Expected: FAIL because `AppContainer` always creates local persistence.

- [ ] **Step 3: Wire Postgres mode in `AppContainer`**

Modify `backend/app/services/container.py` imports:

```python
from app.providers.persistence import InMemoryFavoritesRepository, InMemoryWardrobeRepository
from app.providers.postgres import (
    PostgresAuthStore,
    PostgresDatabase,
    PostgresFavoritesRepository,
    PostgresTaskRepository,
    PostgresTraceRecorder,
    PostgresWardrobeRepository,
)
```

Replace the persistence construction in `AppContainer.__init__` with:

```python
        self.postgres_database = PostgresDatabase(self.settings.postgres_dsn) if self.settings.postgres_dsn else None
        if self.postgres_database is not None:
            self.postgres_database.check_connection()
            self.tracer = PostgresTraceRecorder(self.postgres_database)
            self.auth_store = PostgresAuthStore(
                self.postgres_database,
                session_max_age_days=self.settings.auth_session_max_age_days,
            )
            self.wardrobe_repository = PostgresWardrobeRepository(self.postgres_database)
            self.task_repository = PostgresTaskRepository(self.postgres_database)
            self.favorites_repository = PostgresFavoritesRepository(self.postgres_database)
        else:
            self.tracer = InMemoryTraceRecorder()
            self.auth_store = AuthStore(
                self.settings.auth_store_path,
                session_max_age_days=self.settings.auth_session_max_age_days,
            )
            self.wardrobe_repository = InMemoryWardrobeRepository()
            self.task_repository = None
            self.favorites_repository = InMemoryFavoritesRepository()
```

Pass repositories into `create_task_service`:

```python
        self.task_service: TaskService = create_task_service(
            self.graph,
            self.tracer,
            wardrobe_repository=self.wardrobe_repository,
            favorites_repository=self.favorites_repository,
            repository=self.task_repository,
        )
```

- [ ] **Step 4: Run container tests**

Run:

```bash
cd backend
python -m pytest tests/test_container_persistence.py -q
```

Expected: PASS.

- [ ] **Step 5: Run existing backend tests**

Run:

```bash
cd backend
python -m pytest tests/test_auth.py tests/test_agent_graph.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit Task 4**

```bash
git add backend/app/services/container.py backend/tests/test_container_persistence.py
git commit -m "feat: select postgres persistence from container"
```

---

### Task 5: Favorite Product and Saved Look API

**Files:**
- Modify: `backend/app/api/routes.py`
- Test: `backend/tests/test_favorites_api.py`

- [ ] **Step 1: Write API tests**

Create `backend/tests/test_favorites_api.py`:

```python
from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import create_app
from app.providers.auth import AuthStore
from app.providers.google_auth import GoogleIdTokenVerifier
from app.providers.auth import GoogleProfile
from app.schemas.domain import Budget, Marketplace, ProductCategory, Scene, StyleTaskRequest, TaskStatus
from app.schemas.quality import GateStatus, QualityGateReport, RecommendationReport
from app.schemas.results import StyleTaskResult
from app.services.container import get_container


class FakeGoogleVerifier(GoogleIdTokenVerifier):
    def __init__(self) -> None:
        self.profile = GoogleProfile(
            sub="google-sub-1",
            email="style.user@example.com",
            email_verified=True,
            name="Style User",
            avatar_url="https://example.com/avatar.png",
        )

    def verify(self, id_token: str) -> GoogleProfile:
        return self.profile


def client_with_auth(tmp_path) -> tuple[TestClient, FakeGoogleVerifier]:
    get_container.cache_clear()
    container = get_container()
    container.settings.auth_store_path = tmp_path / "auth.json"
    container.auth_store = AuthStore(container.settings.auth_store_path, session_max_age_days=30)
    verifier = FakeGoogleVerifier()
    container.google_id_token_verifier = verifier
    return TestClient(create_app()), verifier


def login(client: TestClient) -> dict:
    response = client.post("/api/v1/auth/google", json={"id_token": "header.payload.signature"})
    assert response.status_code == 200
    return response.json()


def auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def product_payload(product_id: str = "tmall_100") -> dict:
    return {
        "product_id": product_id,
        "marketplace": "tmall",
        "category": "top",
        "title": "White shirt",
        "price": 199,
        "price_text": "CNY 199",
        "image_url": "https://example.com/shirt.jpg",
        "product_url": "https://detail.tmall.com/item.htm?id=100",
        "shop_name": "Example Shop",
        "sizes": ["M"],
        "colors": ["white"],
        "style_tags": ["clean"],
        "fit_tags": ["regular"],
        "source_reliability": 0.91,
        "score": 0.88,
        "risk_flags": [],
        "raw": {"source": "test"},
    }


def request() -> StyleTaskRequest:
    return StyleTaskRequest(
        photo_url="https://example.com/person.jpg",
        photo_object_key="uploads/person.jpg",
        scene=Scene.daily,
        budget=Budget(min=300, max=800),
        marketplaces=[Marketplace.tmall],
    )


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


def test_favorite_product_create_list_delete_requires_current_user(tmp_path) -> None:
    client, _ = client_with_auth(tmp_path)
    login_body = login(client)
    token = login_body["session"]["token"]

    unauthenticated = client.get("/api/v1/favorite-products")
    assert unauthenticated.status_code == 401

    create = client.post("/api/v1/favorite-products", json=product_payload(), headers=auth_header(token))
    duplicate = client.post("/api/v1/favorite-products", json=product_payload(), headers=auth_header(token))
    listing = client.get("/api/v1/favorite-products", headers=auth_header(token))
    favorite_id = create.json()["favorite_id"]
    deleted = client.delete(f"/api/v1/favorite-products/{favorite_id}", headers=auth_header(token))
    after_delete = client.get("/api/v1/favorite-products", headers=auth_header(token))

    assert create.status_code == 201
    assert duplicate.status_code == 200
    assert duplicate.json()["favorite_id"] == favorite_id
    assert listing.status_code == 200
    assert [item["favorite_id"] for item in listing.json()] == [favorite_id]
    assert deleted.status_code == 200
    assert deleted.json() == {"ok": True}
    assert after_delete.json() == []


def test_users_cannot_delete_each_others_favorites(tmp_path) -> None:
    client, verifier = client_with_auth(tmp_path)
    first = login(client)
    first_token = first["session"]["token"]
    created = client.post("/api/v1/favorite-products", json=product_payload(), headers=auth_header(first_token))
    favorite_id = created.json()["favorite_id"]

    verifier.profile = GoogleProfile(
        sub="google-sub-2",
        email="second@example.com",
        email_verified=True,
        name="Second User",
        avatar_url=None,
    )
    second = login(client)
    second_token = second["session"]["token"]

    blocked = client.delete(f"/api/v1/favorite-products/{favorite_id}", headers=auth_header(second_token))
    second_listing = client.get("/api/v1/favorite-products", headers=auth_header(second_token))

    assert blocked.status_code == 404
    assert second_listing.json() == []


def test_save_look_requires_owned_completed_task(tmp_path) -> None:
    client, _ = client_with_auth(tmp_path)
    login_body = login(client)
    token = login_body["session"]["token"]
    user_id = login_body["user"]["user_id"]
    container = get_container()
    task = container.task_service.create_task(request(), user_id=user_id)
    result = StyleTaskResult(
        task_id=task.task_id,
        status=TaskStatus.partial_succeeded,
        outfit=None,
        recommendation_report=recommendation_report(),
        user_message="partial",
    )
    container.task_service.repository.complete(task.task_id, result)

    incomplete = client.post("/api/v1/style-tasks/missing/save-look", headers=auth_header(token))
    saved = client.post(f"/api/v1/style-tasks/{task.task_id}/save-look", headers=auth_header(token))
    duplicate = client.post(f"/api/v1/style-tasks/{task.task_id}/save-look", headers=auth_header(token))
    listing = client.get("/api/v1/saved-looks", headers=auth_header(token))

    assert incomplete.status_code == 404
    assert saved.status_code == 409
    assert saved.json() == {"detail": "Task has no completed look to save"}
    assert duplicate.status_code == 409
    assert listing.status_code == 200
    assert listing.json() == []
```

After Task 1, `TaskService.save_look()` only saves tasks with an outfit. This first test confirms a partial task without an outfit is rejected; Step 4 adds the valid outfit save path.

- [ ] **Step 2: Run API tests and verify first failure**

Run:

```bash
cd backend
python -m pytest tests/test_favorites_api.py -q
```

Expected: FAIL because the favorite routes do not exist.

- [ ] **Step 3: Add auth requirement helper and routes**

Modify `backend/app/api/routes.py` imports:

```python
from app.schemas.favorites import FavoriteProduct, FavoriteProductCreate, SavedLook
```

Add this helper near `current_user`:

```python
def require_user(user: PublicUser | None) -> PublicUser:
    if user is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user
```

Modify task creation to persist ownership:

```python
    task = container.task_service.create_task(request, user_id=user.user_id if user else None)
```

Add routes:

```python
@router.get("/api/v1/favorite-products", response_model=list[FavoriteProduct])
async def list_favorite_products(
    container: Annotated[AppContainer, Depends(container_dependency)],
    user: Annotated[PublicUser | None, Depends(current_user)],
) -> list[FavoriteProduct]:
    current = require_user(user)
    return container.task_service.list_favorite_products(current.user_id)


@router.post("/api/v1/favorite-products", response_model=FavoriteProduct)
async def create_favorite_product(
    payload: FavoriteProductCreate,
    container: Annotated[AppContainer, Depends(container_dependency)],
    user: Annotated[PublicUser | None, Depends(current_user)],
) -> FavoriteProduct:
    current = require_user(user)
    if payload.source_task_id is not None:
        try:
            if container.task_service.task_owner_id(payload.source_task_id) != current.user_id:
                raise HTTPException(status_code=404, detail="Task not found")
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Task not found") from exc
    existing = next(
        (
            favorite
            for favorite in container.task_service.list_favorite_products(current.user_id)
            if favorite.product_id == payload.product_id and favorite.marketplace == payload.marketplace
        ),
        None,
    )
    favorite = container.task_service.save_favorite_product(current.user_id, payload)
    status_code = 200 if existing is not None else 201
    from fastapi.responses import JSONResponse

    return JSONResponse(status_code=status_code, content=favorite.model_dump(mode="json"))


@router.delete("/api/v1/favorite-products/{favorite_id}")
async def delete_favorite_product(
    favorite_id: str,
    container: Annotated[AppContainer, Depends(container_dependency)],
    user: Annotated[PublicUser | None, Depends(current_user)],
) -> dict[str, bool]:
    current = require_user(user)
    if not container.task_service.delete_favorite_product(current.user_id, favorite_id):
        raise HTTPException(status_code=404, detail="Favorite product not found")
    return {"ok": True}


@router.get("/api/v1/saved-looks", response_model=list[SavedLook])
async def list_saved_looks(
    container: Annotated[AppContainer, Depends(container_dependency)],
    user: Annotated[PublicUser | None, Depends(current_user)],
) -> list[SavedLook]:
    current = require_user(user)
    return container.task_service.list_saved_looks(current.user_id)


@router.post("/api/v1/style-tasks/{task_id}/save-look", response_model=SavedLook)
async def save_style_task_look(
    task_id: str,
    container: Annotated[AppContainer, Depends(container_dependency)],
    user: Annotated[PublicUser | None, Depends(current_user)],
) -> SavedLook:
    current = require_user(user)
    try:
        return container.task_service.save_look(current.user_id, task_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Task not found") from exc
    except PermissionError as exc:
        raise HTTPException(status_code=404, detail="Task not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
```

Move `from fastapi.responses import JSONResponse` to the top-level imports after the test passes once; the inline import above is only to show the exact response behavior needed for 200 versus 201.

- [ ] **Step 4: Add a valid save-look API test**

Extend `backend/tests/test_favorites_api.py` with a helper and test:

```python
from app.schemas.domain import OutfitCandidate, OutfitItem


def outfit() -> OutfitCandidate:
    item = OutfitItem(
        **product_payload(),
        selection_reason="Fits the request",
        match_reason="Matches daily styling",
        selection_scores={"product": 0.88},
    )
    return OutfitCandidate(
        candidate_id="candidate_1",
        title="Clean daily outfit",
        items=[item],
        total_price=199,
        score=0.9,
        score_breakdown={"fit": 0.9},
        why_this_works=["balanced"],
    )


def test_save_completed_look_is_idempotent_and_listed(tmp_path) -> None:
    client, _ = client_with_auth(tmp_path)
    login_body = login(client)
    token = login_body["session"]["token"]
    user_id = login_body["user"]["user_id"]
    container = get_container()
    task = container.task_service.create_task(request(), user_id=user_id)
    result = StyleTaskResult(
        task_id=task.task_id,
        status=TaskStatus.partial_succeeded,
        outfit=outfit(),
        recommendation_report=recommendation_report(),
        user_message="partial",
    )
    container.task_service.repository.complete(task.task_id, result)

    saved = client.post(f"/api/v1/style-tasks/{task.task_id}/save-look", headers=auth_header(token))
    duplicate = client.post(f"/api/v1/style-tasks/{task.task_id}/save-look", headers=auth_header(token))
    listing = client.get("/api/v1/saved-looks", headers=auth_header(token))

    assert saved.status_code == 200
    assert duplicate.status_code == 200
    assert duplicate.json()["look_id"] == saved.json()["look_id"]
    assert [look["look_id"] for look in listing.json()] == [saved.json()["look_id"]]
```

- [ ] **Step 5: Run API tests**

Run:

```bash
cd backend
python -m pytest tests/test_favorites_api.py -q
```

Expected: PASS.

- [ ] **Step 6: Run auth and API tests together**

Run:

```bash
cd backend
python -m pytest tests/test_auth.py tests/test_favorites_api.py -q
```

Expected: PASS.

- [ ] **Step 7: Commit Task 5**

```bash
git add backend/app/api/routes.py backend/tests/test_favorites_api.py
git commit -m "feat: add favorite and saved look api"
```

---

### Task 6: Documentation and Full Verification

**Files:**
- Modify: `backend/README.md`
- Verify: backend tests

- [ ] **Step 1: Update README Postgres configuration**

Add this section to `backend/README.md` after the provider configuration block:

```markdown
## PostgreSQL Persistence

Set `STYLE_BACKEND_POSTGRES_DSN` to use PostgreSQL for production persistence:

```env
STYLE_BACKEND_POSTGRES_DSN=postgresql://postgres:postgres@127.0.0.1:5432/clothes
```

Apply the schema before starting the service:

```bash
psql "$STYLE_BACKEND_POSTGRES_DSN" -f migrations/001_initial.sql
```

When the DSN is configured, users, sessions, style tasks, trace events, wardrobe items, favorite products, and saved looks are written to Postgres. When the DSN is not configured, the backend keeps the local development stores.

For repository integration tests, set a separate test database:

```env
STYLE_BACKEND_TEST_POSTGRES_DSN=postgresql://postgres:postgres@127.0.0.1:5432/clothes_test
```
```

- [ ] **Step 2: Run focused backend tests**

Run:

```bash
cd backend
python -m pytest tests/test_favorites_repository.py tests/test_migration_sql.py tests/test_container_persistence.py tests/test_favorites_api.py -q
```

Expected: PASS.

- [ ] **Step 3: Run existing backend regression tests**

Run:

```bash
cd backend
python -m pytest tests/test_auth.py tests/test_agent_graph.py -q
```

Expected: PASS.

- [ ] **Step 4: Run full backend test suite**

Run:

```bash
cd backend
python -m pytest -q
```

Expected: PASS, with `tests/test_postgres_persistence.py` skipped unless `STYLE_BACKEND_TEST_POSTGRES_DSN` is configured.

- [ ] **Step 5: Run Postgres integration tests when a test DSN is available**

Run:

```bash
cd backend
$env:STYLE_BACKEND_TEST_POSTGRES_DSN="postgresql://postgres:postgres@127.0.0.1:5432/clothes_test"
python -m pytest tests/test_postgres_persistence.py -q
```

Expected with DSN: PASS.

- [ ] **Step 6: Check git diff for accidental unrelated edits**

Run:

```bash
git status --short
git diff --stat
```

Expected: only files from this plan are staged or modified by this implementation. Existing unrelated dirty files may still be present and must not be reverted.

- [ ] **Step 7: Commit Task 6**

```bash
git add backend/README.md
git commit -m "docs: document postgres persistence"
```

---

## Self-Review Checklist

- Spec goal "users and sessions in Postgres" maps to Task 2 and Task 3.
- Spec goal "style task requests, status updates, results, and request ownership" maps to Task 1, Task 3, and Task 5.
- Spec goal "trace events for each task" maps to Task 3.
- Spec goal "wardrobe items" maps to Task 3 and Task 4.
- Spec goal "single-product favorites" maps to Task 1, Task 2, Task 3, and Task 5.
- Spec goal "saved looks" maps to Task 1, Task 2, Task 3, and Task 5.
- Spec goal "local fallback without DSN" maps to Task 4.
- Spec goal "configured DSN fails clearly" maps to `PostgresDatabase.check_connection()` in Task 4.
- Verification commands are listed in Task 6.
