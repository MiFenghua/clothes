from __future__ import annotations

from pydantic import BaseModel, Field

from app.providers.query_planner import ProductSearchPlan
from app.schemas.domain import (
    OutfitCandidate,
    PreferenceConstraints,
    ProductCandidate,
    StyleProfile,
    StyleTaskRequest,
)
from app.schemas.quality import ImageCandidate, ImageQualityReport, RecommendationReport


class StyleGraphState(BaseModel):
    task_id: str
    request: StyleTaskRequest
    profile: StyleProfile | None = None
    constraints: PreferenceConstraints | None = None
    search_queries: list[ProductSearchPlan] = Field(default_factory=list)
    raw_products: list[ProductCandidate] = Field(default_factory=list)
    normalized_products: list[ProductCandidate] = Field(default_factory=list)
    outfit_candidates: list[OutfitCandidate] = Field(default_factory=list)
    selected_outfit: OutfitCandidate | None = None
    recommendation_report: RecommendationReport | None = None
    rejected_outfits: list[OutfitCandidate] = Field(default_factory=list)
    image_prompt: str | None = None
    image_candidates: list[ImageCandidate] = Field(default_factory=list)
    image_quality_reports: list[ImageQualityReport] = Field(default_factory=list)
    accepted_image: ImageCandidate | None = None
    user_message: str | None = None
    blocking_reason: str | None = None
