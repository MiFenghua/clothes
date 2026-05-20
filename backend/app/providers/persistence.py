from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Protocol
from uuid import uuid4

from app.schemas.domain import Marketplace, ProductCandidate, StyleTaskRequest, TaskStatus, WardrobeItem
from app.schemas.favorites import FavoriteProduct, FavoriteProductCreate, SavedLook
from app.schemas.results import StyleTaskResult, StyleTaskView


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def canonical_task_owner_id(user_id: str | None = None, owner_id: str | None = None) -> str | None:
    if user_id is not None and owner_id is not None and user_id != owner_id:
        raise ValueError("Task owner mismatch")
    return user_id if user_id is not None else owner_id


class TaskRepository(Protocol):
    def create(
        self,
        task_id: str,
        request: StyleTaskRequest,
        user_id: str | None = None,
        owner_id: str | None = None,
    ) -> StyleTaskView:
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

    def list_recent_completed(self, owner_id: str | None = None, limit: int = 6) -> list[StyleTaskView]:
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


@dataclass
class InMemoryTaskRepository:
    tasks: dict[str, StyleTaskView] = field(default_factory=dict)
    task_owner_ids: dict[str, str | None] = field(default_factory=dict)

    def create(
        self,
        task_id: str,
        request: StyleTaskRequest,
        user_id: str | None = None,
        owner_id: str | None = None,
    ) -> StyleTaskView:
        canonical_owner_id = canonical_task_owner_id(user_id=user_id, owner_id=owner_id)
        task = StyleTaskView(
            task_id=task_id,
            owner_id=canonical_owner_id,
            status=TaskStatus.created,
            progress=2,
            message="任务已创建",
            request=request,
            created_at=now_utc(),
            updated_at=now_utc(),
        )
        self.tasks[task_id] = task
        self.task_owner_ids[task_id] = canonical_owner_id
        return task

    def update_status(self, task_id: str, status: TaskStatus, message: str, progress: int) -> StyleTaskView:
        task = self.get(task_id)
        updated = task.model_copy(update={"status": status, "message": message, "progress": progress, "updated_at": now_utc()})
        self.tasks[task_id] = updated
        return updated

    def complete(self, task_id: str, result: StyleTaskResult) -> StyleTaskView:
        task = self.get(task_id)
        status = result.status
        progress = 100 if status in {TaskStatus.succeeded, TaskStatus.partial_succeeded} else task.progress
        updated = task.model_copy(
            update={
                "status": status,
                "message": result.user_message or ("搭配完成" if status == TaskStatus.succeeded else "推荐完成，试穿图未通过质检"),
                "progress": progress,
                "result": result,
                "updated_at": now_utc(),
            }
        )
        self.tasks[task_id] = updated
        return updated

    def fail(self, task_id: str, message: str) -> StyleTaskView:
        task = self.get(task_id)
        updated = task.model_copy(
            update={"status": TaskStatus.failed, "message": message, "progress": 100, "error": message, "updated_at": now_utc()}
        )
        self.tasks[task_id] = updated
        return updated

    def get(self, task_id: str) -> StyleTaskView:
        if task_id not in self.tasks:
            raise KeyError(f"Task not found: {task_id}")
        return self.tasks[task_id]

    def owner_id(self, task_id: str) -> str | None:
        self.get(task_id)
        return self.task_owner_ids.get(task_id)

    def list_recent_completed(self, owner_id: str | None = None, limit: int = 6) -> list[StyleTaskView]:
        completed = [
            task
            for task in self.tasks.values()
            if self.task_owner_ids.get(task.task_id) == owner_id
            and task.result is not None
            and task.status in {TaskStatus.succeeded, TaskStatus.partial_succeeded}
        ]
        completed.sort(key=lambda task: task.updated_at, reverse=True)
        return completed[:limit]


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
        favorite = FavoriteProduct(
            **product.model_dump(),
            favorite_id=f"favorite_{uuid4().hex[:16]}",
            user_id=user_id,
            created_at=now_utc(),
        )
        self.favorite_products[favorite.favorite_id] = favorite
        return favorite

    def list_products(self, user_id: str) -> list[FavoriteProduct]:
        favorites = [favorite for favorite in self.favorite_products.values() if favorite.user_id == user_id]
        favorites.sort(key=lambda favorite: favorite.created_at, reverse=True)
        return favorites

    def delete_product(self, user_id: str, favorite_id: str) -> bool:
        favorite = self.favorite_products.get(favorite_id)
        if favorite is None or favorite.user_id != user_id:
            return False
        del self.favorite_products[favorite_id]
        return True

    def save_look(self, user_id: str, task: StyleTaskView) -> SavedLook:
        if task.result is None or task.result.recommendation_report is None:
            raise ValueError("Task has no completed look to save")
        for look in self.saved_looks.values():
            if look.user_id == user_id and look.source_task_id == task.task_id:
                return look
        look = SavedLook(
            look_id=f"look_{uuid4().hex[:16]}",
            user_id=user_id,
            source_task_id=task.task_id,
            outfit=task.result.outfit.model_copy(deep=True) if task.result.outfit is not None else None,
            recommendation_report=task.result.recommendation_report.model_copy(deep=True),
            try_on_image_url=task.result.try_on_image_url,
            image_quality_report=task.result.image_quality_report.model_copy(deep=True)
            if task.result.image_quality_report is not None
            else None,
            created_at=now_utc(),
        )
        self.saved_looks[look.look_id] = look
        return look

    def list_looks(self, user_id: str) -> list[SavedLook]:
        looks = [look for look in self.saved_looks.values() if look.user_id == user_id]
        looks.sort(key=lambda look: look.created_at, reverse=True)
        return looks


@dataclass
class InMemoryWardrobeRepository:
    items: dict[str, WardrobeItem] = field(default_factory=dict)

    def list_for_user(self, owner_id: str | None = None) -> list[WardrobeItem]:
        return [item for item in self.items.values() if owner_id is None or item.owner_id == owner_id]

    def save(self, item: WardrobeItem) -> WardrobeItem:
        self.items[item.item_id] = item
        return item

    def products_for_ids(self, item_ids: list[str]) -> list[ProductCandidate]:
        products: list[ProductCandidate] = []
        for item_id in item_ids:
            item = self.items.get(item_id)
            if item is None:
                continue
            products.append(
                ProductCandidate(
                    product_id=item.item_id,
                    marketplace=Marketplace.owned,
                    category=item.category,
                    title=item.title,
                    price=0,
                    price_text="衣橱已有",
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
