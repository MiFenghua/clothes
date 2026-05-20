from __future__ import annotations

from typing import Any

from app.providers.tracing import InMemoryTraceRecorder


class OpenTelemetryTraceRecorder(InMemoryTraceRecorder):
    """Trace recorder that mirrors local trace events into OpenTelemetry spans."""

    def __init__(self, service_name: str) -> None:
        super().__init__()
        try:
            from opentelemetry import trace
            from opentelemetry.sdk.resources import Resource
            from opentelemetry.sdk.trace import TracerProvider
        except Exception as exc:  # pragma: no cover - optional production dependency
            raise RuntimeError("opentelemetry-api and opentelemetry-sdk are required") from exc
        provider = TracerProvider(resource=Resource.create({"service.name": service_name}))
        trace.set_tracer_provider(provider)
        self.otel_tracer = trace.get_tracer(service_name)

    def record(self, task_id: str, node: str, event: str, payload: dict[str, Any]) -> None:
        super().record(task_id, node, event, payload)
        with self.otel_tracer.start_as_current_span(f"{node}.{event}") as span:
            span.set_attribute("task_id", task_id)
            span.set_attribute("agent.node", node)
            span.set_attribute("agent.event", event)
            for key, value in payload.items():
                if isinstance(value, str | int | float | bool):
                    span.set_attribute(f"payload.{key}", value)

