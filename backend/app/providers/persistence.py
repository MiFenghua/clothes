from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Protocol

from app.schemas.domain import Marketplace, ProductCandidate, StyleTaskRequest, TaskStatus, WardrobeItem
from app.schemas.results import StyleTaskResult, StyleTaskView


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


class TaskRepository(Protocol):
    def create(self, task_id: str, request: StyleTaskRequest) -> StyleTaskView:
        ...

    def update_status(self, task_id: str, status: TaskStatus, message: str, progress: int) -> StyleTaskView:
        ...

    def complete(self, task_id: str, result: StyleTaskResult) -> StyleTaskView:
        ...

    def fail(self, task_id: str, message: str) -> StyleTaskView:
        ...

    def get(self, task_id: str) -> StyleTaskView:
        ...


@dataclass
class InMemoryTaskRepository:
    tasks: dict[str, StyleTaskView] = field(default_factory=dict)

    def create(self, task_id: str, request: StyleTaskRequest) -> StyleTaskView:
        task = StyleTaskView(
            task_id=task_id,
            status=TaskStatus.created,
            progress=2,
            message="任务已创建",
            request=request,
            created_at=now_utc(),
            updated_at=now_utc(),
        )
        self.tasks[task_id] = task
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
