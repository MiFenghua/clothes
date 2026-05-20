from __future__ import annotations

from datetime import timedelta

try:
    from temporalio import workflow
except Exception:  # pragma: no cover - allows importing without Temporal installed

    class _WorkflowCompat:
        def defn(self, cls):
            return cls

        def run(self, fn):
            return fn

    workflow = _WorkflowCompat()  # type: ignore[assignment]


@workflow.defn
class StyleTaskWorkflow:
    """Temporal wrapper for durable long-running style tasks.

    The local FastAPI service can execute the same graph in-process. Production should route
    task creation through this workflow so retries, timeouts, and recovery are durable.
    """

    @workflow.run
    async def run(self, task_id: str) -> str:
        # Temporal activities are intentionally thin wrappers around TaskService methods.
        # They are registered in `temporal_worker.py` where application dependencies exist.
        return await workflow.execute_activity(
            "run_style_task_activity",
            task_id,
            start_to_close_timeout=timedelta(minutes=8),
        )

