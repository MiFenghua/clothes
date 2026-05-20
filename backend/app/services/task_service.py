from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

from app.agents.graph import StyleAgentGraph
from app.providers.persistence import InMemoryTaskRepository, InMemoryWardrobeRepository, TaskRepository
from app.providers.tracing import InMemoryTraceRecorder
from app.schemas.domain import StyleTaskRequest, TaskStatus, WardrobeItem
from app.schemas.results import StyleTaskResult, StyleTaskView


@dataclass
class TaskService:
    repository: TaskRepository
    wardrobe_repository: InMemoryWardrobeRepository
    graph: StyleAgentGraph
    tracer: InMemoryTraceRecorder

    def create_task(self, request: StyleTaskRequest) -> StyleTaskView:
        task_id = f"task_{uuid4().hex[:16]}"
        return self.repository.create(task_id, request)

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
            return self.repository.fail(task_id, "任务执行失败，请稍后重试。")

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
            return self.repository.fail(task_id, "试穿图重新生成失败，请稍后重试。")

    def get_task(self, task_id: str) -> StyleTaskView:
        return self.repository.get(task_id)

    def get_result(self, task_id: str) -> StyleTaskResult:
        task = self.repository.get(task_id)
        if task.result is None:
            raise ValueError("Task result is not ready")
        return task.result

    def save_wardrobe_item(self, item: WardrobeItem) -> WardrobeItem:
        return self.wardrobe_repository.save(item)

    def list_wardrobe_items(self, owner_id: str | None = None) -> list[WardrobeItem]:
        return self.wardrobe_repository.list_for_user(owner_id)


def create_task_service(
    graph: StyleAgentGraph,
    tracer: InMemoryTraceRecorder,
    wardrobe_repository: InMemoryWardrobeRepository | None = None,
) -> TaskService:
    return TaskService(
        repository=InMemoryTaskRepository(),
        wardrobe_repository=wardrobe_repository or InMemoryWardrobeRepository(),
        graph=graph,
        tracer=tracer,
    )
