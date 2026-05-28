from __future__ import annotations

from typing import Protocol

from pydantic import BaseModel, Field

from app.config import Settings
from app.schemas.domain import PreferenceConstraints, ProductCategory, StyleProfile, StyleTaskRequest


class SearchQueryPlanner(Protocol):
    source: str

    async def build_queries(
        self,
        *,
        request: StyleTaskRequest,
        profile: StyleProfile,
        constraints: PreferenceConstraints,
    ) -> list["ProductSearchPlan"]:
        ...


class ProductSearchPlan(BaseModel):
    query: str = Field(min_length=1, max_length=120)
    category: ProductCategory
    colors: list[str] = Field(default_factory=list)
    style_tags: list[str] = Field(default_factory=list)
    fit_tags: list[str] = Field(default_factory=list)


class SearchQueryPlan(BaseModel):
    queries: list[ProductSearchPlan] = Field(default_factory=list, min_length=2, max_length=6)


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
    ) -> list[ProductSearchPlan]:
        payload = await self.vision.create_json(prompt=self._prompt(request, profile, constraints), image_urls=[])
        plan = SearchQueryPlan.model_validate(payload)
        queries = [query for query in plan.queries if query.query.strip()]
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
  "queries": [
    {{
      "query": "concrete Chinese ecommerce search phrase",
      "category": "top | bottom | dress | outerwear | shoes | bag | accessory",
      "colors": ["model extracted color terms"],
      "style_tags": ["model extracted style terms"],
      "fit_tags": ["model extracted fit terms"]
    }}
  ]
}}

Rules:
- Each query object must be directly derived from the model-extracted profile and user input.
- Do not rely on backend category inference; provide the category explicitly.
- For Taobao Union, only use categories supported by the configured category table: top, bottom, dress, outerwear, shoes, bag, accessory.
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
