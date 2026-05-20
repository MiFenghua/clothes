from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from app.providers.auth import GoogleProfile
from app.providers.persistence import TaskRepository, canonical_task_owner_id, now_utc
from app.schemas.auth import AuthSession, AuthUserRecord, PublicUser
from app.schemas.domain import Marketplace, OutfitCandidate, ProductCandidate, StyleTaskRequest, TaskStatus, WardrobeItem
from app.schemas.favorites import FavoriteProduct, FavoriteProductCreate, SavedLook
from app.schemas.quality import ImageQualityReport, RecommendationReport
from app.schemas.results import StyleTaskResult, StyleTaskView


class PostgresDatabase:
    def __init__(self, dsn: str) -> None:
        self.dsn = dsn

    def connect(self) -> psycopg.Connection[dict[str, Any]]:
        return psycopg.connect(self.dsn, row_factory=dict_row)

    def check_connection(self) -> bool:
        with self.connect() as conn:
            conn.execute("SELECT 1")
        return True


def _database(database: PostgresDatabase | str) -> PostgresDatabase:
    if isinstance(database, PostgresDatabase):
        return database
    return PostgresDatabase(database)


class PostgresAuthStore:
    def __init__(self, database: PostgresDatabase | str, session_max_age_days: int) -> None:
        self.database = _database(database)
        self.session_max_age_days = session_max_age_days

    def upsert_google_user(self, profile: GoogleProfile) -> AuthUserRecord:
        if not profile.email_verified:
            raise ValueError("Google profile email must be verified")

        email = profile.email.strip().lower()
        now = self._now()
        with self.database.connect() as conn:
            user_by_sub = self._find_user_by_google_sub(conn, profile.sub)
            user_by_email = self._find_user_by_email(conn, email)
            if user_by_sub is not None and user_by_email is not None and user_by_sub["user_id"] != user_by_email["user_id"]:
                raise ValueError("Google profile email belongs to another user")

            user = user_by_sub or user_by_email
            if user is not None:
                row = conn.execute(
                    """
                    UPDATE auth_users
                    SET google_sub = %s,
                        email = %s,
                        name = %s,
                        avatar_url = %s,
                        updated_at = %s
                    WHERE user_id = %s
                    RETURNING *
                    """,
                    (
                        profile.sub,
                        email,
                        profile.name or user["name"],
                        profile.avatar_url or user["avatar_url"],
                        now,
                        user["user_id"],
                    ),
                ).fetchone()
                if row is None:
                    raise KeyError(f"Auth user not found: {user['user_id']}")
                return self._auth_user(row)

            row = conn.execute(
                """
                INSERT INTO auth_users (user_id, google_sub, email, name, avatar_url, provider, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, 'google', %s, %s)
                RETURNING *
                """,
                (
                    f"user_{uuid4().hex[:16]}",
                    profile.sub,
                    email,
                    profile.name or email.split("@")[0] or "Google User",
                    profile.avatar_url,
                    now,
                    now,
                ),
            ).fetchone()
            if row is None:
                raise RuntimeError("Auth user insert did not return a row")
            return self._auth_user(row)

    def create_session(self, user_id: str) -> AuthSession:
        self._prune_expired_sessions()
        now = self._now()
        expires_at = now + timedelta(days=self.session_max_age_days)
        token = secrets.token_urlsafe(32)
        with self.database.connect() as conn:
            exists = conn.execute("SELECT 1 FROM auth_users WHERE user_id = %s", (user_id,)).fetchone()
            if exists is None:
                raise ValueError(f"Unknown auth user: {user_id}")
            conn.execute(
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
        with self.database.connect() as conn:
            row = conn.execute(
                """
                SELECT u.*
                FROM auth_sessions s
                JOIN auth_users u ON u.user_id = s.user_id
                WHERE s.token_hash = %s
                  AND s.expires_at > %s
                """,
                (self._hash_token(token), self._now()),
            ).fetchone()
        return self._public_user(row) if row is not None else None

    def destroy_session(self, token: str | None) -> None:
        if not token:
            return
        with self.database.connect() as conn:
            conn.execute("DELETE FROM auth_sessions WHERE token_hash = %s", (self._hash_token(token),))

    def _prune_expired_sessions(self) -> None:
        with self.database.connect() as conn:
            conn.execute("DELETE FROM auth_sessions WHERE expires_at <= %s", (self._now(),))

    @staticmethod
    def _find_user_by_google_sub(conn: psycopg.Connection[dict[str, Any]], google_sub: str) -> dict[str, Any] | None:
        return conn.execute("SELECT * FROM auth_users WHERE google_sub = %s", (google_sub,)).fetchone()

    @staticmethod
    def _find_user_by_email(conn: psycopg.Connection[dict[str, Any]], email: str) -> dict[str, Any] | None:
        return conn.execute("SELECT * FROM auth_users WHERE email = %s", (email,)).fetchone()

    @staticmethod
    def _hash_token(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    @staticmethod
    def _now() -> datetime:
        return datetime.now(UTC)

    @staticmethod
    def _auth_user(row: dict[str, Any]) -> AuthUserRecord:
        return AuthUserRecord.model_validate(row)

    @staticmethod
    def _public_user(row: dict[str, Any]) -> PublicUser:
        return PublicUser.model_validate(row)


class PostgresTaskRepository:
    def __init__(self, database: PostgresDatabase | str) -> None:
        self.database = _database(database)

    def create(
        self,
        task_id: str,
        request: StyleTaskRequest,
        user_id: str | None = None,
        owner_id: str | None = None,
    ) -> StyleTaskView:
        canonical_owner_id = canonical_task_owner_id(user_id=user_id, owner_id=owner_id)
        now = now_utc()
        with self.database.connect() as conn:
            row = conn.execute(
                """
                INSERT INTO style_tasks (task_id, user_id, status, progress, message, request, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING *
                """,
                (
                    task_id,
                    canonical_owner_id,
                    TaskStatus.created.value,
                    2,
                    "Task created",
                    Jsonb(request.model_dump(mode="json")),
                    now,
                    now,
                ),
            ).fetchone()
        if row is None:
            raise RuntimeError("Task insert did not return a row")
        return self._style_task(row)

    def update_status(self, task_id: str, status: TaskStatus, message: str, progress: int) -> StyleTaskView:
        with self.database.connect() as conn:
            row = conn.execute(
                """
                UPDATE style_tasks
                SET status = %s,
                    message = %s,
                    progress = %s,
                    updated_at = %s
                WHERE task_id = %s
                RETURNING *
                """,
                (status.value, message, progress, now_utc(), task_id),
            ).fetchone()
        return self._require_task(row, task_id)

    def complete(self, task_id: str, result: StyleTaskResult) -> StyleTaskView:
        message = result.user_message or (
            "Styling complete"
            if result.status == TaskStatus.succeeded
            else "Recommendations complete; try-on image did not pass quality checks"
        )
        with self.database.connect() as conn:
            row = conn.execute(
                """
                UPDATE style_tasks
                SET status = %s,
                    message = %s,
                    progress = CASE
                        WHEN %s = ANY(%s) THEN 100
                        ELSE progress
                    END,
                    result = %s,
                    updated_at = %s
                WHERE task_id = %s
                RETURNING *
                """,
                (
                    result.status.value,
                    message,
                    result.status.value,
                    [TaskStatus.succeeded.value, TaskStatus.partial_succeeded.value],
                    Jsonb(result.model_dump(mode="json")),
                    now_utc(),
                    task_id,
                ),
            ).fetchone()
        return self._require_task(row, task_id)

    def fail(self, task_id: str, message: str) -> StyleTaskView:
        with self.database.connect() as conn:
            row = conn.execute(
                """
                UPDATE style_tasks
                SET status = %s,
                    message = %s,
                    progress = 100,
                    error = %s,
                    updated_at = %s
                WHERE task_id = %s
                RETURNING *
                """,
                (TaskStatus.failed.value, message, message, now_utc(), task_id),
            ).fetchone()
        return self._require_task(row, task_id)

    def get(self, task_id: str) -> StyleTaskView:
        with self.database.connect() as conn:
            row = conn.execute("SELECT * FROM style_tasks WHERE task_id = %s", (task_id,)).fetchone()
        return self._require_task(row, task_id)

    def owner_id(self, task_id: str) -> str | None:
        with self.database.connect() as conn:
            row = conn.execute("SELECT user_id FROM style_tasks WHERE task_id = %s", (task_id,)).fetchone()
        if row is None:
            raise KeyError(f"Task not found: {task_id}")
        return row["user_id"]

    def list_recent_completed(self, owner_id: str | None = None, limit: int = 6) -> list[StyleTaskView]:
        with self.database.connect() as conn:
            rows = conn.execute(
                """
                SELECT *
                FROM style_tasks
                WHERE user_id IS NOT DISTINCT FROM %s
                  AND result IS NOT NULL
                  AND status = ANY(%s)
                ORDER BY updated_at DESC
                LIMIT %s
                """,
                (owner_id, [TaskStatus.succeeded.value, TaskStatus.partial_succeeded.value], limit),
            ).fetchall()
        return [self._style_task(row) for row in rows]

    @staticmethod
    def _require_task(row: dict[str, Any] | None, task_id: str) -> StyleTaskView:
        if row is None:
            raise KeyError(f"Task not found: {task_id}")
        return PostgresTaskRepository._style_task(row)

    @staticmethod
    def _style_task(row: dict[str, Any]) -> StyleTaskView:
        result = row["result"]
        return StyleTaskView(
            task_id=row["task_id"],
            owner_id=row["user_id"],
            status=TaskStatus(row["status"]),
            progress=row["progress"],
            message=row["message"],
            request=StyleTaskRequest.model_validate(row["request"]),
            result=StyleTaskResult.model_validate(result) if result is not None else None,
            error=row["error"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )


class PostgresTraceRecorder:
    def __init__(self, database: PostgresDatabase | str) -> None:
        self.database = _database(database)

    def record(self, task_id: str, node: str, event: str, payload: dict[str, Any]) -> None:
        with self.database.connect() as conn:
            conn.execute(
                """
                INSERT INTO trace_events (task_id, node, event, payload)
                VALUES (%s, %s, %s, %s)
                """,
                (task_id, node, event, Jsonb(payload)),
            )

    def by_task(self, task_id: str) -> list[dict[str, Any]]:
        with self.database.connect() as conn:
            rows = conn.execute(
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
    def __init__(self, database: PostgresDatabase | str) -> None:
        self.database = _database(database)

    def list_for_user(self, owner_id: str | None = None) -> list[WardrobeItem]:
        with self.database.connect() as conn:
            if owner_id is None:
                rows = conn.execute("SELECT * FROM wardrobe_items ORDER BY created_at DESC").fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM wardrobe_items WHERE owner_id = %s ORDER BY created_at DESC",
                    (owner_id,),
                ).fetchall()
        return [self._wardrobe_item(row) for row in rows]

    def save(self, item: WardrobeItem) -> WardrobeItem:
        now = now_utc()
        with self.database.connect() as conn:
            row = conn.execute(
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
        if row is None:
            raise RuntimeError("Wardrobe item upsert did not return a row")
        return self._wardrobe_item(row)

    def products_for_ids(self, item_ids: list[str]) -> list[ProductCandidate]:
        if not item_ids:
            return []
        with self.database.connect() as conn:
            rows = conn.execute("SELECT * FROM wardrobe_items WHERE item_id = ANY(%s)", (item_ids,)).fetchall()
        items_by_id = {row["item_id"]: self._wardrobe_item(row) for row in rows}
        products: list[ProductCandidate] = []
        for item_id in item_ids:
            item = items_by_id.get(item_id)
            if item is None:
                continue
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

    @staticmethod
    def _wardrobe_item(row: dict[str, Any]) -> WardrobeItem:
        return WardrobeItem(
            item_id=row["item_id"],
            owner_id=row["owner_id"],
            category=row["category"],
            image_url=row["image_url"],
            title=row["title"],
            colors=row["colors"],
            style_tags=row["style_tags"],
            fit_tags=row["fit_tags"],
            notes=row["notes"],
        )


class PostgresFavoritesRepository:
    def __init__(self, database: PostgresDatabase | str) -> None:
        self.database = _database(database)

    def save_product(self, user_id: str, product: FavoriteProductCreate) -> FavoriteProduct:
        with self.database.connect() as conn:
            row = conn.execute(
                """
                INSERT INTO favorite_products (
                    favorite_id, user_id, product_id, marketplace, category, title, price, price_text,
                    image_url, product_url, shop_name, sizes, colors, style_tags, fit_tags,
                    source_reliability, score, risk_flags, raw, source_task_id
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (user_id, product_id, marketplace) DO UPDATE
                SET product_id = EXCLUDED.product_id
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
        if row is None:
            raise RuntimeError("Favorite product upsert did not return a row")
        return self._favorite_product(row)

    def list_products(self, user_id: str) -> list[FavoriteProduct]:
        with self.database.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM favorite_products WHERE user_id = %s ORDER BY created_at DESC",
                (user_id,),
            ).fetchall()
        return [self._favorite_product(row) for row in rows]

    def delete_product(self, user_id: str, favorite_id: str) -> bool:
        with self.database.connect() as conn:
            cursor = conn.execute(
                "DELETE FROM favorite_products WHERE user_id = %s AND favorite_id = %s",
                (user_id, favorite_id),
            )
            return cursor.rowcount > 0

    def save_look(self, user_id: str, task: StyleTaskView) -> SavedLook:
        if task.result is None or task.result.recommendation_report is None:
            raise ValueError("Task has no completed look to save")

        with self.database.connect() as conn:
            existing = conn.execute(
                """
                SELECT *
                FROM saved_looks
                WHERE user_id = %s
                  AND source_task_id IS NOT DISTINCT FROM %s
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (user_id, task.task_id),
            ).fetchone()
            if existing is not None:
                return self._saved_look(existing)

            row = conn.execute(
                """
                INSERT INTO saved_looks (
                    look_id, user_id, source_task_id, outfit, recommendation_report, try_on_image_url, image_quality_report
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING *
                """,
                (
                    f"look_{uuid4().hex[:16]}",
                    user_id,
                    task.task_id,
                    Jsonb(task.result.outfit.model_dump(mode="json")) if task.result.outfit is not None else None,
                    Jsonb(task.result.recommendation_report.model_dump(mode="json")),
                    task.result.try_on_image_url,
                    Jsonb(task.result.image_quality_report.model_dump(mode="json"))
                    if task.result.image_quality_report is not None
                    else None,
                ),
            ).fetchone()
        if row is None:
            raise RuntimeError("Saved look insert did not return a row")
        return self._saved_look(row)

    def list_looks(self, user_id: str) -> list[SavedLook]:
        with self.database.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM saved_looks WHERE user_id = %s ORDER BY created_at DESC",
                (user_id,),
            ).fetchall()
        return [self._saved_look(row) for row in rows]

    @staticmethod
    def _favorite_product(row: dict[str, Any]) -> FavoriteProduct:
        return FavoriteProduct(
            favorite_id=row["favorite_id"],
            user_id=row["user_id"],
            product_id=row["product_id"],
            marketplace=row["marketplace"],
            category=row["category"],
            title=row["title"],
            price=row["price"],
            price_text=row["price_text"],
            image_url=row["image_url"],
            product_url=row["product_url"],
            shop_name=row["shop_name"],
            sizes=row["sizes"],
            colors=row["colors"],
            style_tags=row["style_tags"],
            fit_tags=row["fit_tags"],
            source_reliability=row["source_reliability"],
            score=row["score"],
            risk_flags=row["risk_flags"],
            raw=row["raw"],
            source_task_id=row["source_task_id"],
            created_at=row["created_at"],
        )

    @staticmethod
    def _saved_look(row: dict[str, Any]) -> SavedLook:
        outfit = row["outfit"]
        recommendation_report = row["recommendation_report"]
        image_quality_report = row["image_quality_report"]
        return SavedLook(
            look_id=row["look_id"],
            user_id=row["user_id"],
            source_task_id=row["source_task_id"],
            outfit=OutfitCandidate.model_validate(outfit) if outfit is not None else None,
            recommendation_report=RecommendationReport.model_validate(recommendation_report),
            try_on_image_url=row["try_on_image_url"],
            image_quality_report=ImageQualityReport.model_validate(image_quality_report)
            if image_quality_report is not None
            else None,
            created_at=row["created_at"],
        )


def create_postgres_repository(dsn: str | None) -> TaskRepository | None:
    if not dsn:
        return None
    return PostgresTaskRepository(PostgresDatabase(dsn))
