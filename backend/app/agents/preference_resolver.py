from __future__ import annotations

from app.agents.state import StyleGraphState
from app.providers.tracing import TraceRecorder
from app.schemas.domain import PreferenceConstraints


class PreferenceResolverAgent:
    node_name = "PreferenceResolverAgent"

    def __init__(self, tracer: TraceRecorder) -> None:
        self.tracer = tracer

    async def run(self, state: StyleGraphState) -> StyleGraphState:
        if state.profile is None:
            raise ValueError("Style profile is required before resolving preferences")
        preferences = state.request.preferences
        positive = self._split(preferences.liked_style) or state.profile.style_signals
        negative = self._split(preferences.avoid)
        constraints = PreferenceConstraints(
            scene=state.request.scene,
            budget=state.request.budget,
            positive_style_terms=positive,
            negative_style_terms=negative,
            required_fit_terms=state.profile.fit_advice,
            palette=state.profile.palette,
            marketplaces=state.request.marketplaces,
            wardrobe_item_ids=state.request.wardrobe_item_ids,
        )
        self.tracer.record(state.task_id, self.node_name, "constraints_resolved", constraints.model_dump())
        return state.model_copy(update={"constraints": constraints})

    def _split(self, value: str | None) -> list[str]:
        if not value:
            return []
        return [part.strip() for part in value.replace("，", ",").replace("、", ",").split(",") if part.strip()]

