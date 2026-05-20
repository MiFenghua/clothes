from __future__ import annotations

from collections import Counter
from itertools import islice, product
from uuid import uuid5, NAMESPACE_URL

from app.agents.state import StyleGraphState
from app.providers.tracing import TraceRecorder
from app.schemas.domain import OutfitCandidate, OutfitItem, ProductCandidate, ProductCategory, Scene


class StylistComposerAgent:
    node_name = "StylistComposerAgent"

    def __init__(self, tracer: TraceRecorder) -> None:
        self.tracer = tracer

    async def run(self, state: StyleGraphState) -> StyleGraphState:
        if state.constraints is None or state.profile is None:
            raise ValueError("Profile and constraints are required before outfit composition")
        grouped = self._group_products(state.normalized_products)
        category_paths = self._category_paths(state.constraints.scene, grouped)
        candidates: list[OutfitCandidate] = []
        for path in category_paths:
            pools = [list(islice(grouped.get(category, []), 4)) for category in path]
            if any(not pool for pool in pools):
                continue
            for combination in islice(product(*pools), 8):
                items = [self._to_item(product_item, state, category_index=index) for index, product_item in enumerate(combination)]
                candidate_id = uuid5(NAMESPACE_URL, "|".join(item.product_id for item in items)).hex[:12]
                total_price = sum(item.price for item in items)
                base_score = sum(item.score for item in items) / len(items)
                budget_score = self._budget_score(total_price, state)
                coherence = self._coherence_score(items, state)
                score = round(base_score * 0.52 + budget_score * 0.2 + coherence * 0.28, 4)
                candidates.append(
                    OutfitCandidate(
                        candidate_id=f"outfit_{candidate_id}",
                        title=self._title_for(state),
                        items=items,
                        total_price=round(total_price, 2),
                        score=score,
                        score_breakdown={
                            "product_quality": round(base_score, 4),
                            "budget": round(budget_score, 4),
                            "coherence": round(coherence, 4),
                        },
                        why_this_works=[
                            "单品版型围绕高腰线和干净轮廓组织，能强化比例。",
                            "配色控制在低饱和基础色，适合用户场景并降低出错率。",
                        ],
                        risk_flags=[risk for item in items for risk in item.risk_flags],
                    )
                )
        candidates.sort(key=lambda candidate: candidate.score, reverse=True)
        candidates = candidates[:5]
        self.tracer.record(
            state.task_id,
            self.node_name,
            "outfits_composed",
            {
                "candidate_count": len(candidates),
                "category_counts": self._category_counts(state.normalized_products),
                "attempted_paths": [[category.value for category in path] for path in category_paths],
            },
        )
        return state.model_copy(update={"outfit_candidates": candidates})

    def _group_products(self, products: list[ProductCandidate]) -> dict[ProductCategory, list[ProductCandidate]]:
        grouped: dict[ProductCategory, list[ProductCandidate]] = {}
        for item in products:
            grouped.setdefault(item.category, []).append(item)
        for values in grouped.values():
            values.sort(key=lambda product_item: product_item.score, reverse=True)
        return grouped

    def _category_paths(
        self, scene: Scene, grouped: dict[ProductCategory, list[ProductCandidate]]
    ) -> list[list[ProductCategory]]:
        separates_full = [ProductCategory.top, ProductCategory.bottom, ProductCategory.shoes, ProductCategory.bag]
        separates_shoes = [ProductCategory.top, ProductCategory.bottom, ProductCategory.shoes]
        separates_bag = [ProductCategory.top, ProductCategory.bottom, ProductCategory.bag]
        separates_core = [ProductCategory.top, ProductCategory.bottom]
        dress_full = [ProductCategory.dress, ProductCategory.shoes, ProductCategory.bag]
        dress_shoes = [ProductCategory.dress, ProductCategory.shoes]
        dress_bag = [ProductCategory.dress, ProductCategory.bag]
        commute_full = [ProductCategory.top, ProductCategory.bottom, ProductCategory.outerwear, ProductCategory.shoes]
        commute_outerwear = [ProductCategory.top, ProductCategory.bottom, ProductCategory.outerwear]

        if scene == Scene.date:
            preferred = [dress_full, dress_shoes, dress_bag, separates_full, separates_shoes, separates_bag, separates_core]
        elif scene == Scene.commute:
            preferred = [commute_full, commute_outerwear, separates_full, separates_shoes, separates_bag, separates_core]
        else:
            preferred = [separates_full, separates_shoes, separates_bag, separates_core, dress_full, dress_shoes, dress_bag]

        viable: list[list[ProductCategory]] = []
        seen: set[tuple[ProductCategory, ...]] = set()
        for path in preferred:
            key = tuple(path)
            if key in seen:
                continue
            seen.add(key)
            if all(grouped.get(category) for category in path):
                viable.append(path)
        return viable

    def _category_counts(self, products: list[ProductCandidate]) -> dict[str, int]:
        return dict(Counter(product.category.value for product in products))

    def _to_item(self, product_item: ProductCandidate, state: StyleGraphState, category_index: int) -> OutfitItem:
        fit_reason = "版型与当前比例建议匹配"
        if product_item.fit_tags:
            fit_reason = f"包含{'、'.join(product_item.fit_tags[:2])}等版型线索"
        return OutfitItem(
            **product_item.model_dump(),
            selection_reason=f"第 {category_index + 1} 件单品用于建立完整穿搭层次，{fit_reason}。",
            match_reason=f"{product_item.title} 与 {state.request.scene.value} 场景、预算和偏好方向匹配。",
            selection_scores={
                "product": product_item.score,
                "source": product_item.source_reliability,
            },
        )

    def _budget_score(self, total_price: float, state: StyleGraphState) -> float:
        max_budget = state.request.budget.max
        min_budget = state.request.budget.min
        if max_budget and total_price > max_budget:
            return max(0.2, 1 - (total_price - max_budget) / max(max_budget, 1))
        if min_budget and total_price < min_budget * 0.55:
            return 0.75
        return 1

    def _coherence_score(self, items: list[OutfitItem], state: StyleGraphState) -> float:
        palette_matches = 0
        if state.constraints:
            palette = set(state.constraints.palette)
            palette_matches = sum(1 for item in items if palette.intersection(item.colors))
        severe_risks = sum(1 for item in items for risk in item.risk_flags if risk.startswith("severe:"))
        return max(0, min(1, 0.74 + palette_matches * 0.05 - severe_risks * 0.25))

    def _title_for(self, state: StyleGraphState) -> str:
        scene_title = {
            Scene.daily: "清爽显比例日常穿搭",
            Scene.commute: "利落轻熟通勤穿搭",
            Scene.date: "温柔精致约会穿搭",
            Scene.travel: "舒适上镜旅行穿搭",
            Scene.party: "精致有氛围聚会穿搭",
        }[state.request.scene]
        return scene_title
