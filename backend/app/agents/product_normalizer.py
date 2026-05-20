from __future__ import annotations

from app.agents.quality_gates import data_gate_for_product
from app.agents.state import StyleGraphState
from app.providers.tracing import TraceRecorder


class ProductNormalizerAgent:
    node_name = "ProductNormalizerAgent"

    def __init__(self, tracer: TraceRecorder) -> None:
        self.tracer = tracer

    async def run(self, state: StyleGraphState) -> StyleGraphState:
        if state.constraints is None:
            raise ValueError("Preference constraints are required before product normalization")
        normalized = []
        for product in state.raw_products:
            risk_flags = list(product.risk_flags)
            title_blob = " ".join([product.title, *product.style_tags, *product.fit_tags]).lower()
            for avoid in state.constraints.negative_style_terms:
                if avoid and avoid.lower() in title_blob:
                    risk_flags.append(f"severe:命中避雷项:{avoid}")
            report = data_gate_for_product(product)
            score = product.score * 0.55 + product.source_reliability * 0.25 + report.score * 0.2
            if risk_flags:
                score -= 0.12 * len([risk for risk in risk_flags if risk.startswith("severe:")])
            normalized.append(
                product.model_copy(
                    update={
                        "score": max(0, min(1, score)),
                        "risk_flags": risk_flags,
                        "source_reliability": max(product.source_reliability, report.score),
                    }
                )
            )
        normalized.sort(key=lambda item: item.score, reverse=True)
        self.tracer.record(
            state.task_id,
            self.node_name,
            "products_normalized",
            {"input_count": len(state.raw_products), "output_count": len(normalized)},
        )
        return state.model_copy(update={"normalized_products": normalized})

