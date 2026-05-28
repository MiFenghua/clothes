from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

from app.agents.graph import StyleAgentGraph
from app.providers.persistence import (
    FavoritesRepository,
    InMemoryFavoritesRepository,
    InMemoryTaskRepository,
    InMemoryWardrobeRepository,
    TaskRepository,
    WardrobeRepository,
    canonical_task_owner_id,
)
from app.providers.tracing import TraceRecorder
from app.schemas.domain import StyleTaskRequest, TaskStatus, WardrobeItem
from app.schemas.favorites import FavoriteProduct, FavoriteProductCreate, SavedLook
from app.schemas.results import StyleTaskResult, StyleTaskView


@dataclass
class TaskService:
    repository: TaskRepository
    favorites_repository: FavoritesRepository
    wardrobe_repository: WardrobeRepository
    graph: StyleAgentGraph
    tracer: TraceRecorder

    def create_task(
        self,
        request: StyleTaskRequest,
        user_id: str | None = None,
        owner_id: str | None = None,
    ) -> StyleTaskView:
        task_id = f"task_{uuid4().hex[:16]}"
        canonical_owner_id = canonical_task_owner_id(user_id=user_id, owner_id=owner_id)
        return self.repository.create(task_id, request, user_id=canonical_owner_id, owner_id=canonical_owner_id)

    async def run_task(self, task_id: str) -> StyleTaskView:
        task = self.repository.get(task_id)

        async def update_status(status: TaskStatus, message: str, progress: int) -> None:
            self.repository.update_status(task_id, status, message, progress)

        try:
            result = await self.graph.run(task_id=task_id, request=task.request, status_callback=update_status)
            if result.status == TaskStatus.failed:
                self.repository.complete(task_id, result)
                return self.repository.fail(task_id, result.user_message or "任务失败")
            return self.repository.complete(task_id, result)
        except Exception as exc:
            self.tracer.record(task_id, "TaskService", "task_failed", {"error": str(exc)})
            return self.repository.fail(task_id, f"任务执行异常：{exc}")

    async def retry_image(self, task_id: str) -> StyleTaskView:
        task = self.repository.get(task_id)
        if task.result is None or task.result.outfit is None:
            raise ValueError("Task has no approved outfit to retry")
        self.repository.update_status(task_id, TaskStatus.generating_candidates, "正在重新生成试穿效果图", 76)

        async def update_status(status: TaskStatus, message: str, progress: int) -> None:
            self.repository.update_status(task_id, status, message, progress)

        try:
            result = await self.graph.retry_image(
                task_id=task_id,
                request=task.request,
                outfit=task.result.outfit,
                recommendation_report=task.result.recommendation_report,
                rejected_outfits=task.result.alternatives_rejected,
                status_callback=update_status,
            )
            return self.repository.complete(task_id, result)
        except Exception as exc:
            self.tracer.record(task_id, "TaskService", "image_retry_failed", {"error": str(exc)})
            return self.repository.fail(task_id, f"试穿图重新生成异常：{exc}")

    def get_task(self, task_id: str) -> StyleTaskView:
        return self.repository.get(task_id)

    def task_owner_id(self, task_id: str) -> str | None:
        return self.repository.owner_id(task_id)

    def get_result(self, task_id: str) -> StyleTaskResult:
        task = self.repository.get(task_id)
        if task.result is None:
            raise ValueError("Task result is not ready")
        return task.result

    def recent_completed_tasks(self, owner_id: str | None = None, limit: int = 6) -> list[StyleTaskView]:
        return self.repository.list_recent_completed(owner_id=owner_id, limit=limit)

    def save_wardrobe_item(self, item: WardrobeItem) -> WardrobeItem:
        return self.wardrobe_repository.save(item)

    def list_wardrobe_items(self, owner_id: str | None = None) -> list[WardrobeItem]:
        return self.wardrobe_repository.list_for_user(owner_id)

    def save_favorite_product(self, user_id: str, product: FavoriteProductCreate) -> FavoriteProduct:
        if product.source_task_id is not None:
            try:
                owner_id = self.repository.owner_id(product.source_task_id)
            except KeyError as exc:
                raise PermissionError("Task not found") from exc
            if owner_id != user_id:
                raise PermissionError("Task not found")
        return self.favorites_repository.save_product(user_id, product)

    def list_favorite_products(self, user_id: str) -> list[FavoriteProduct]:
        return self.favorites_repository.list_products(user_id)

    def delete_favorite_product(self, user_id: str, favorite_id: str) -> bool:
        return self.favorites_repository.delete_product(user_id, favorite_id)

    def save_look(self, user_id: str, task_id: str) -> SavedLook:
        task = self.repository.get(task_id)
        if self.repository.owner_id(task_id) != user_id:
            raise PermissionError("Task not found")
        if (
            task.status not in {TaskStatus.succeeded, TaskStatus.partial_succeeded}
            or task.result is None
            or task.result.outfit is None
            or task.result.recommendation_report is None
        ):
            raise ValueError("Task has no completed look to save")
        return self.favorites_repository.save_look(user_id, task)

    def list_saved_looks(self, user_id: str) -> list[SavedLook]:
        return self.favorites_repository.list_looks(user_id)


def create_task_service(
    graph: StyleAgentGraph,
    tracer: TraceRecorder,
    wardrobe_repository: WardrobeRepository | None = None,
    favorites_repository: FavoritesRepository | None = None,
    repository: TaskRepository | None = None,
) -> TaskService:
    return TaskService(
        repository=repository or InMemoryTaskRepository(),
        favorites_repository=favorites_repository or InMemoryFavoritesRepository(),
        wardrobe_repository=wardrobe_repository or InMemoryWardrobeRepository(),
        graph=graph,
        tracer=tracer,
    )
