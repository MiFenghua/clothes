from __future__ import annotations

from app.agents.state import StyleGraphState
from app.providers.tracing import TraceRecorder


class FitCriticAgent:
    node_name = "FitCriticAgent"

    def __init__(self, tracer: TraceRecorder, threshold: float) -> None:
        self.tracer = tracer
        self.threshold = threshold

    async def run(self, state: StyleGraphState) -> StyleGraphState:
        if state.constraints is None:
            raise ValueError("Preference constraints are required before fit criticism")

        # Invariant: styling suitability is a model decision. This node only preserves
        # model-scored candidates in rank order so downstream gates can enforce data,
        # explanation, and threshold requirements without lexical rescoring.
        reviewed = sorted(state.outfit_candidates, key=lambda candidate: candidate.score, reverse=True)
        self.tracer.record(
            state.task_id,
            self.node_name,
            "outfits_reviewed",
            {
                "candidate_count": len(reviewed),
                "top_score": reviewed[0].score if reviewed else 0,
                "threshold": self.threshold,
            },
        )
        return state.model_copy(update={"outfit_candidates": reviewed})
