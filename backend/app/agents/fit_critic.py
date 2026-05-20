from __future__ import annotations

from app.agents.quality_gates import data_gate_for_outfit, explanation_gate, styling_gate
from app.agents.state import StyleGraphState
from app.providers.tracing import TraceRecorder
from app.schemas.domain import OutfitCandidate
from app.schemas.quality import RecommendationReport


class FitCriticAgent:
    node_name = "FitCriticAgent"

    def __init__(self, tracer: TraceRecorder, threshold: float) -> None:
        self.tracer = tracer
        self.threshold = threshold

    async def run(self, state: StyleGraphState) -> StyleGraphState:
        if state.constraints is None:
            raise ValueError("Preference constraints are required before fit criticism")
        reviewed: list[OutfitCandidate] = []
        reports: dict[str, RecommendationReport] = {}
        for candidate in state.outfit_candidates:
            report = self._review_candidate(candidate, state)
            gates = [data_gate_for_outfit(candidate), explanation_gate(candidate)]
            report = report.model_copy(update={"gates": [*gates, styling_gate(report, self.threshold)]})
            reports[candidate.candidate_id] = report
            gate_penalty = 0.25 if any(gate.blocking for gate in report.gates) else 0
            reviewed.append(candidate.model_copy(update={"score": max(0, report.final_score - gate_penalty)}))
        reviewed.sort(key=lambda candidate: candidate.score, reverse=True)
        self.tracer.record(
            state.task_id,
            self.node_name,
            "outfits_reviewed",
            {
                "candidate_count": len(reviewed),
                "top_score": reviewed[0].score if reviewed else 0,
                "reports": {key: value.model_dump() for key, value in reports.items()},
            },
        )
        return state.model_copy(update={"outfit_candidates": reviewed})

    def _review_candidate(self, candidate: OutfitCandidate, state: StyleGraphState) -> RecommendationReport:
        assert state.constraints is not None
        budget_score = candidate.score_breakdown.get("budget", 0.75)
        risk_flags = list(candidate.risk_flags)
        fit_score = self._term_score([*state.constraints.required_fit_terms, *state.constraints.positive_style_terms], candidate)
        color_score = self._term_score(state.constraints.palette, candidate, fields=("colors",))
        occasion_score = self._term_score(state.constraints.positive_style_terms or [state.request.scene.value], candidate)
        wardrobe_score = 0.9 if not state.constraints.wardrobe_item_ids else self._wardrobe_score(candidate)
        severe_risk_count = len([risk for risk in risk_flags if risk.startswith("severe:")])
        final = (
            fit_score * 0.25
            + color_score * 0.18
            + occasion_score * 0.2
            + budget_score * 0.17
            + wardrobe_score * 0.08
            + candidate.score_breakdown.get("product_quality", 0.7) * 0.12
            - severe_risk_count * 0.18
        )
        return RecommendationReport(
            final_score=round(max(0, min(1, final)), 4),
            fit_score=round(fit_score, 4),
            color_score=round(color_score, 4),
            occasion_score=round(occasion_score, 4),
            budget_score=round(budget_score, 4),
            wardrobe_score=round(wardrobe_score, 4),
            gates=[],
            risk_flags=risk_flags,
            why_this_works=candidate.why_this_works,
            why_not_others=candidate.why_not_others,
        )

    def _term_score(
        self,
        terms: list[str],
        candidate: OutfitCandidate,
        fields: tuple[str, ...] = ("title", "style_tags", "fit_tags"),
    ) -> float:
        if not terms:
            return 0.78
        hits = 0
        blob_parts: list[str] = []
        for item in candidate.items:
            if "title" in fields:
                blob_parts.append(item.title)
            if "style_tags" in fields:
                blob_parts.extend(item.style_tags)
            if "fit_tags" in fields:
                blob_parts.extend(item.fit_tags)
            if "colors" in fields:
                blob_parts.extend(item.colors)
        blob = " ".join(blob_parts).lower()
        for term in terms:
            if term and term.lower() in blob:
                hits += 1
        return min(1, 0.72 + hits * 0.07)

    def _wardrobe_score(self, candidate: OutfitCandidate) -> float:
        owned_count = len([item for item in candidate.items if item.marketplace == "owned"])
        return min(1, 0.72 + owned_count * 0.12)

