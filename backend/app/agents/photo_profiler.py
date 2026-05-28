from __future__ import annotations

from app.agents.state import StyleGraphState
from app.providers.tracing import TraceRecorder
from app.providers.vision import PhotoProfileProvider


class PhotoProfilerAgent:
    node_name = "PhotoProfilerAgent"

    def __init__(self, tracer: TraceRecorder, provider: PhotoProfileProvider | None = None) -> None:
        self.tracer = tracer
        self.provider = provider

    async def run(self, state: StyleGraphState) -> StyleGraphState:
        if self.provider is None:
            raise RuntimeError("照片画像模型不可用：未配置视觉模型。")
        try:
            profile = await self.provider.analyze(task_id=state.task_id, request=state.request)
        except Exception as exc:
            self.tracer.record(state.task_id, self.node_name, "profile_provider_failed", {"error": str(exc)})
            raise RuntimeError(f"照片画像模型异常：{exc}") from exc
        self.tracer.record(state.task_id, self.node_name, "profile_created", profile.model_dump())
        return state.model_copy(update={"profile": profile})
