from __future__ import annotations

from uuid import NAMESPACE_URL, uuid5

from app.agents.state import StyleGraphState
from app.providers.outfit_planner import ModelOutfitCandidatePlan, OutfitPlanner
from app.providers.tracing import TraceRecorder
from app.schemas.domain import OutfitCandidate, OutfitItem, ProductCandidate


class StylistComposerAgent:
    node_name = "StylistComposerAgent"

    def __init__(self, tracer: TraceRecorder, planner: OutfitPlanner | None = None) -> None:
        self.tracer = tracer
        self.planner = planner

    async def run(self, state: StyleGraphState) -> StyleGraphState:
        if state.constraints is None or state.profile is None:
            raise ValueError("Profile and constraints are required before outfit composition")
        if self.planner is None:
            raise RuntimeError("模型搭配生成器不可用：未配置穿搭组合模型。")
        if not state.normalized_products:
            raise RuntimeError("模型搭配生成异常：没有可供模型选择的商品。")

        plans = await self.planner.build_outfits(
            request=state.request,
            profile=state.profile,
            constraints=state.constraints,
            products=state.normalized_products,
        )
        product_by_id = {product.product_id: product for product in state.normalized_products}
        candidates = [self._candidate_from_plan(plan, product_by_id) for plan in plans]
        candidates.sort(key=lambda candidate: candidate.score, reverse=True)
        candidates = candidates[:5]

        self.tracer.record(
            state.task_id,
            self.node_name,
            "outfits_composed",
            {
                "candidate_count": len(candidates),
                "planner_source": self.planner.source,
                "selected_product_ids": [[item.product_id for item in candidate.items] for candidate in candidates],
            },
        )
        return state.model_copy(update={"outfit_candidates": candidates})

    def _candidate_from_plan(
        self,
        plan: ModelOutfitCandidatePlan,
        product_by_id: dict[str, ProductCandidate],
    ) -> OutfitCandidate:
        missing_ids = [item.product_id for item in plan.items if item.product_id not in product_by_id]
        if missing_ids:
            raise RuntimeError(f"模型搭配方案引用了不存在商品: {', '.join(missing_ids)}")

        items: list[OutfitItem] = []
        for item_plan in plan.items:
            product = product_by_id[item_plan.product_id]
            items.append(
                OutfitItem(
                    **product.model_dump(),
                    selection_reason=item_plan.selection_reason,
                    match_reason=item_plan.match_reason,
                    selection_scores=item_plan.selection_scores,
                )
            )

        candidate_key = "|".join(item.product_id for item in items)
        return OutfitCandidate(
            candidate_id=f"outfit_{uuid5(NAMESPACE_URL, candidate_key).hex[:12]}",
            title=plan.title,
            items=items,
            total_price=round(sum(item.price for item in items), 2),
            score=plan.score,
            score_breakdown=plan.score_breakdown,
            why_this_works=plan.why_this_works,
            why_not_others=plan.why_not_others,
            risk_flags=[*plan.risk_flags, *[risk for item in items for risk in item.risk_flags]],
        )
