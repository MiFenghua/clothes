from __future__ import annotations

from typing import Protocol

from pydantic import BaseModel, Field

from app.config import Settings
from app.schemas.domain import PreferenceConstraints, ProductCategory, Scene, StyleProfile, StyleTaskRequest


class SearchQueryPlanner(Protocol):
    source: str

    async def build_queries(
        self,
        *,
        request: StyleTaskRequest,
        profile: StyleProfile,
        constraints: PreferenceConstraints,
    ) -> list[str]:
        ...


class SearchQueryPlan(BaseModel):
    queries: list[str] = Field(default_factory=list, min_length=2, max_length=6)


class LocalSearchQueryPlanner:
    """Deterministic fallback used only when no production model planner is configured."""

    source = "local_fallback"

    async def build_queries(
        self,
        *,
        request: StyleTaskRequest,
        profile: StyleProfile,
        constraints: PreferenceConstraints,
    ) -> list[str]:
        style = " ".join(constraints.positive_style_terms[:3])
        fit = " ".join(constraints.required_fit_terms[:2])
        palette = " ".join(constraints.palette[:2])
        scene_words = {
            Scene.daily: ["short top women daily", "high waist straight pants women daily", "low heel shoes women", "small bag women"],
            Scene.commute: ["shirt women office", "high waist tailored pants women", "light jacket women office", "low heel shoes women"],
            Scene.date: ["waist defining dress women date", "low heel shoes women soft", "small square bag women"],
            Scene.travel: ["photogenic top women travel", "high waist casual pants women travel", "comfortable flat shoes women", "light crossbody bag women"],
            Scene.party: ["statement top women party", "high waist skirt women party", "low heel shoes women elegant", "necklace women elegant"],
        }[constraints.scene]
        queries = [f"{query} {style} {fit} {palette}".strip() for query in scene_words]
        if not any(self._category_hint(query) == ProductCategory.shoes for query in queries):
            queries.append(f"low heel shoes women {style} versatile".strip())
        return queries[:5]

    def _category_hint(self, query: str) -> ProductCategory:
        lowered = query.lower()
        if "shoe" in lowered or "flat" in lowered or "heel" in lowered:
            return ProductCategory.shoes
        if "pants" in lowered or "skirt" in lowered:
            return ProductCategory.bottom
        if "bag" in lowered:
            return ProductCategory.bag
        if "dress" in lowered:
            return ProductCategory.dress
        return ProductCategory.top


class ArkSearchQueryPlanner:
    source = "ark_model"

    def __init__(self, settings: Settings) -> None:
        from app.providers.vision import ArkVisionClient

        self.vision = ArkVisionClient(settings)

    async def build_queries(
        self,
        *,
        request: StyleTaskRequest,
        profile: StyleProfile,
        constraints: PreferenceConstraints,
    ) -> list[str]:
        payload = await self.vision.create_json(prompt=self._prompt(request, profile, constraints), image_urls=[])
        plan = SearchQueryPlan.model_validate(payload)
        queries = [query.strip() for query in plan.queries if query and query.strip()]
        if len(queries) < 2:
            raise RuntimeError("Ark query planner returned too few search queries")
        return queries[:6]

    def _prompt(
        self,
        request: StyleTaskRequest,
        profile: StyleProfile,
        constraints: PreferenceConstraints,
    ) -> str:
        preferences = request.preferences
        return f"""You are an ecommerce outfit search planner for a women's AI stylist app.
Create search keywords from the model-extracted photo profile and explicit user constraints.
Do not use fixed templates. Do not invent attributes that are not supported by the profile or user input.

Return strict JSON only:
{{
  "queries": ["2-6 concise ecommerce search queries"]
}}

Rules:
- Each query must be a Chinese ecommerce search phrase.
- Each query must include one concrete product category term and 1-3 model/user extracted terms.
- Cover enough categories for an outfit: top+bottom plus shoes or bag, or dress plus shoes or bag.
- Prefer real marketplace language suitable for Taobao/Tmall and Taobao Union material search.
- Avoid terms listed by the user.

Inputs:
- scene: {constraints.scene.value}
- budget_min: {request.budget.min}
- budget_max: {request.budget.max}
- user_liked_style: {preferences.liked_style or ""}
- user_avoid: {preferences.avoid or ""}
- profile_style_signals: {", ".join(profile.style_signals)}
- profile_fit_advice: {", ".join(profile.fit_advice)}
- profile_palette: {", ".join(profile.palette)}
- profile_summary: {profile.summary}
- positive_style_terms: {", ".join(constraints.positive_style_terms)}
- required_fit_terms: {", ".join(constraints.required_fit_terms)}
- palette: {", ".join(constraints.palette)}
"""
