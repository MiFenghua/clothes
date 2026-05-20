from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Protocol


class TraceRecorder(Protocol):
    def record(self, task_id: str, node: str, event: str, payload: dict[str, Any]) -> None:
        ...


@dataclass
class InMemoryTraceRecorder:
    events: list[dict[str, Any]] = field(default_factory=list)

    def record(self, task_id: str, node: str, event: str, payload: dict[str, Any]) -> None:
        self.events.append(
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "task_id": task_id,
                "node": node,
                "event": event,
                "payload": payload,
            }
        )

    def by_task(self, task_id: str) -> list[dict[str, Any]]:
        return [event for event in self.events if event["task_id"] == task_id]

