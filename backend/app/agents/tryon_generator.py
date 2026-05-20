from __future__ import annotations

from app.agents.state import StyleGraphState
from app.providers.image import TryOnImageProvider
from app.providers.tracing import TraceRecorder


class TryOnGeneratorAgent:
    node_name = "TryOnGeneratorAgent"

    def __init__(self, tracer: TraceRecorder, image_provider: TryOnImageProvider) -> None:
        self.tracer = tracer
        self.image_provider = image_provider

    async def run(self, state: StyleGraphState, *, attempt: int, count: int = 3) -> StyleGraphState:
        if state.selected_outfit is None or state.image_prompt is None:
            raise ValueError("Selected outfit and image prompt are required before try-on generation")
        candidates = await self.image_provider.generate_candidates(
            task_id=state.task_id,
            request=state.request,
            outfit=state.selected_outfit,
            prompt=state.image_prompt,
            attempt=attempt,
            count=count,
        )
        self.tracer.record(
            state.task_id,
            self.node_name,
            "image_candidates_generated",
            {"attempt": attempt, "candidate_ids": [candidate.candidate_id for candidate in candidates]},
        )
        return state.model_copy(update={"image_candidates": [*state.image_candidates, *candidates]})

