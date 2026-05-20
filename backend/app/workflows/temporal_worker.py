from __future__ import annotations

import asyncio

try:
    from temporalio import activity
    from temporalio.client import Client
    from temporalio.worker import Worker
except Exception:  # pragma: no cover - optional production runtime
    activity = None
    Client = None
    Worker = None

from app.services.container import get_container
from app.workflows.style_workflow import StyleTaskWorkflow


if activity is not None:

    @activity.defn(name="run_style_task_activity")
    async def run_style_task_activity(task_id: str) -> str:
        container = get_container()
        task = await container.task_service.run_task(task_id)
        return task.status.value


async def main() -> None:
    if Client is None or Worker is None:
        raise RuntimeError("temporalio is not installed")
    container = get_container()
    client = await Client.connect(container.settings.temporal_address)
    worker = Worker(
        client,
        task_queue=container.settings.temporal_task_queue,
        workflows=[StyleTaskWorkflow],
        activities=[run_style_task_activity],
    )
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())

