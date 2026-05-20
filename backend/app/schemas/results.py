from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field

from app.schemas.domain import OutfitCandidate, StyleTaskRequest, TaskStatus
from app.schemas.quality import ImageQualityReport, RecommendationReport


class StyleTaskResult(BaseModel):
    task_id: str
    status: TaskStatus
    outfit: OutfitCandidate | None = None
    try_on_image_url: str | None = None
    recommendation_report: RecommendationReport | None = None
    image_quality_report: ImageQualityReport | None = None
    alternatives_rejected: list[OutfitCandidate] = Field(default_factory=list)
    user_message: str | None = None


class TraceEvent(BaseModel):
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    task_id: str
    node: str
    event: str
    payload: dict


class StyleTaskView(BaseModel):
    task_id: str
    status: TaskStatus
    progress: int
    message: str
    request: StyleTaskRequest
    result: StyleTaskResult | None = None
    error: str | None = None
    created_at: datetime
    updated_at: datetime

