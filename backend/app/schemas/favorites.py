from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.schemas.domain import OutfitCandidate, ProductCandidate
from app.schemas.quality import ImageQualityReport, RecommendationReport


class FavoriteProductCreate(ProductCandidate):
    source_task_id: str | None = None


class FavoriteProduct(ProductCandidate):
    favorite_id: str
    user_id: str
    source_task_id: str | None = None
    created_at: datetime


class SavedLook(BaseModel):
    look_id: str
    user_id: str
    source_task_id: str | None = None
    outfit: OutfitCandidate | None = None
    recommendation_report: RecommendationReport
    try_on_image_url: str | None = None
    image_quality_report: ImageQualityReport | None = None
    created_at: datetime
