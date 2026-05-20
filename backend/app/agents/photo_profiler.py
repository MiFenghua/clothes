from __future__ import annotations

from app.agents.state import StyleGraphState
from app.providers.vision import PhotoProfileProvider
from app.providers.tracing import TraceRecorder
from app.schemas.domain import PhotoQuality, StyleProfile


class LocalPhotoProfileProvider:
    async def analyze(self, *, task_id: str, request) -> StyleProfile:
        preferences = request.preferences
        liked = self._split(preferences.liked_style)
        style_signals = liked or ["干净", "显比例", "日常"]
        height = preferences.height_cm
        body_proportion = "petite" if height and height < 160 else "tall" if height and height >= 170 else "balanced"
        profile = StyleProfile(
            body_proportion=body_proportion,
            undertone="neutral",
            hair_tone="dark",
            style_signals=style_signals,
            fit_advice=["高腰线", "线条干净", "避免压身高"],
            palette=["ivory", "denim", "black", "misty pink"],
            photo_quality=PhotoQuality(
                is_full_body=True,
                face_visible=True,
                lighting="good",
                occlusion="low",
                resolution_score=0.86,
            ),
            confidence=0.82,
            summary="照片质量可用，适合基于比例、场景和偏好生成穿搭。",
        )
        return profile

    def _split(self, value: str | None) -> list[str]:
        if not value:
            return []
        return [part.strip() for part in value.replace("，", ",").replace("、", ",").split(",") if part.strip()]


class PhotoProfilerAgent:
    node_name = "PhotoProfilerAgent"

    def __init__(
        self,
        tracer: TraceRecorder,
        provider: PhotoProfileProvider | None = None,
        allow_provider_fallback: bool = True,
    ) -> None:
        self.tracer = tracer
        self.provider = provider or LocalPhotoProfileProvider()
        self.fallback = LocalPhotoProfileProvider()
        self.allow_provider_fallback = allow_provider_fallback

    async def run(self, state: StyleGraphState) -> StyleGraphState:
        try:
            profile = await self.provider.analyze(task_id=state.task_id, request=state.request)
        except Exception as exc:
            self.tracer.record(state.task_id, self.node_name, "profile_provider_failed", {"error": str(exc)})
            if not self.allow_provider_fallback:
                raise
            profile = await self.fallback.analyze(task_id=state.task_id, request=state.request)
        self.tracer.record(state.task_id, self.node_name, "profile_created", profile.model_dump())
        return state.model_copy(update={"profile": profile})
