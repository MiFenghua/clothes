from __future__ import annotations

from app.agents.quality_gates import data_gate_for_outfit, explanation_gate, styling_gate
from app.agents.state import StyleGraphState
from app.providers.tracing import TraceRecorder
from app.schemas.quality import RecommendationReport


class FashionDirectorAgent:
    node_name = "FashionDirectorAgent"

    def __init__(self, tracer: TraceRecorder, threshold: float) -> None:
        self.tracer = tracer
        self.threshold = threshold

    async def run(self, state: StyleGraphState) -> StyleGraphState:
        if not state.outfit_candidates or state.constraints is None:
            return state.model_copy(update={"blocking_reason": "没有足够可信的商品组成完整穿搭。"})
        selected = state.outfit_candidates[0]
        report = self._director_report(selected, state)
        blocking = [gate for gate in report.gates if gate.blocking]
        rejected = state.outfit_candidates[1:]
        if blocking:
            self.tracer.record(
                state.task_id,
                self.node_name,
                "recommendation_rejected",
                {"candidate_id": selected.candidate_id, "blocking": [gate.model_dump() for gate in blocking]},
            )
            return state.model_copy(
                update={
                    "selected_outfit": selected,
                    "recommendation_report": report,
                    "rejected_outfits": rejected,
                    "blocking_reason": "推荐未通过质量闸门，宁缺毋滥。",
                }
            )
        self.tracer.record(
            state.task_id,
            self.node_name,
            "recommendation_selected",
            {"candidate_id": selected.candidate_id, "score": report.final_score},
        )
        return state.model_copy(
            update={"selected_outfit": selected, "recommendation_report": report, "rejected_outfits": rejected}
        )

    def _director_report(self, selected, state: StyleGraphState) -> RecommendationReport:
        fit = selected.score_breakdown.get("coherence", selected.score)
        product = selected.score_breakdown.get("product_quality", selected.score)
        budget = selected.score_breakdown.get("budget", selected.score)
        severe_risks = [risk for risk in selected.risk_flags if risk.startswith("severe:")]
        final = max(0, min(1, selected.score - len(severe_risks) * 0.2))
        report = RecommendationReport(
            final_score=round(final, 4),
            fit_score=round(fit, 4),
            color_score=round(product, 4),
            occasion_score=round(fit, 4),
            budget_score=round(budget, 4),
            wardrobe_score=0.9,
            gates=[],
            risk_flags=selected.risk_flags,
            why_this_works=selected.why_this_works,
            why_not_others=[f"淘汰 {item.candidate_id}：综合适配度低于最终方案" for item in state.outfit_candidates[1:]],
        )
        gates = [data_gate_for_outfit(selected), explanation_gate(selected), styling_gate(report, self.threshold)]
        return report.model_copy(update={"gates": gates})

