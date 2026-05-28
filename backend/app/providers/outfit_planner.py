from __future__ import annotations

import json
from typing import Protocol

from pydantic import BaseModel, Field

from app.config import Settings
from app.schemas.domain import PreferenceConstraints, ProductCandidate, StyleProfile, StyleTaskRequest


class ModelOutfitItemPlan(BaseModel):
    product_id: str = Field(min_length=1)
    selection_reason: str = Field(min_length=1)
    match_reason: str = Field(min_length=1)
    selection_scores: dict[str, float] = Field(default_factory=dict)


class ModelOutfitCandidatePlan(BaseModel):
    title: str = Field(min_length=1)
    items: list[ModelOutfitItemPlan] = Field(min_length=1, max_length=6)
    score: float = Field(ge=0, le=1)
    score_breakdown: dict[str, float] = Field(default_factory=dict)
    why_this_works: list[str] = Field(min_length=2)
    why_not_others: list[str] = Field(default_factory=list)
    risk_flags: list[str] = Field(default_factory=list)


class ModelOutfitPlan(BaseModel):
    outfits: list[ModelOutfitCandidatePlan] = Field(min_length=1, max_length=5)


class OutfitPlanner(Protocol):
    source: str

    async def build_outfits(
        self,
        *,
        request: StyleTaskRequest,
        profile: StyleProfile,
        constraints: PreferenceConstraints,
        products: list[ProductCandidate],
    ) -> list[ModelOutfitCandidatePlan]:
        ...


class ArkOutfitPlanner:
    source = "ark_model"

    def __init__(self, settings: Settings) -> None:
        from app.providers.vision import ArkVisionClient

        self.vision = ArkVisionClient(settings)

    async def build_outfits(
        self,
        *,
        request: StyleTaskRequest,
        profile: StyleProfile,
        constraints: PreferenceConstraints,
        products: list[ProductCandidate],
    ) -> list[ModelOutfitCandidatePlan]:
        payload = await self.vision.create_json(prompt=self._prompt(request, profile, constraints, products), image_urls=[])
        plan = ModelOutfitPlan.model_validate(payload)
        return plan.outfits

    def _prompt(
        self,
        request: StyleTaskRequest,
        profile: StyleProfile,
        constraints: PreferenceConstraints,
        products: list[ProductCandidate],
    ) -> str:
        catalog = [
            {
                "product_id": product.product_id,
                "category": product.category.value,
                "title": product.title,
                "price": product.price,
                "colors": product.colors,
                "style_tags": product.style_tags,
                "fit_tags": product.fit_tags,
                "source_reliability": product.source_reliability,
                "score": product.score,
                "risk_flags": product.risk_flags,
            }
            for product in products
        ]
        return f"""You are the outfit planner for a women's AI stylist app.
Choose 1-5 complete outfit candidates only from the provided product catalog.
The backend will not infer categories, style tags, colors, fit, or fallback combinations.
If the catalog cannot form a credible outfit, return no valid outfit so the task fails visibly.

Return strict JSON only:
{{
  "outfits": [
    {{
      "title": "outfit title",
      "items": [
        {{
          "product_id": "must exactly match a catalog product_id",
          "selection_reason": "why this item is selected",
          "match_reason": "why this item fits the user and outfit",
          "selection_scores": {{"fit": 0.0, "color": 0.0, "scene": 0.0}}
        }}
      ],
      "score": 0.0,
      "score_breakdown": {{"fit": 0.0, "color": 0.0, "scene": 0.0, "budget": 0.0, "product_quality": 0.0}},
      "why_this_works": ["at least two user-facing reasons"],
      "why_not_others": ["optional rejected-composition notes"],
      "risk_flags": ["optional risks; use severe: prefix only for blocking risks"]
    }}
  ]
}}

Rules:
- Use only product_id values from catalog.
- Select items because they work together for the user, not because of fixed backend category paths.
- Score must represent your professional confidence in fit, color, scene, budget, and product credibility.
- Every selected item needs a selection_reason and match_reason.
- Do not hide uncertainty; put material risks in risk_flags.

Inputs:
- scene: {constraints.scene.value}
- budget_min: {request.budget.min}
- budget_max: {request.budget.max}
- user_liked_style: {request.preferences.liked_style or ""}
- user_avoid: {request.preferences.avoid or ""}
- profile_summary: {profile.summary}
- profile_style_signals: {", ".join(profile.style_signals)}
- profile_fit_advice: {", ".join(profile.fit_advice)}
- profile_palette: {", ".join(profile.palette)}
- positive_style_terms: {", ".join(constraints.positive_style_terms)}
- required_fit_terms: {", ".join(constraints.required_fit_terms)}
- palette: {", ".join(constraints.palette)}
- product_catalog: {json.dumps(catalog, ensure_ascii=False)}
"""
