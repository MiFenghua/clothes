from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

from app.schemas.auth import PublicUser
from app.schemas.domain import Scene


class FeatureMetric(BaseModel):
    label: str
    value: str


class StyleProfileUpdate(BaseModel):
    display_name: str | None = Field(default=None, max_length=80)
    height_cm: int | None = Field(default=None, ge=100, le=230)
    weight_kg: int | None = Field(default=None, ge=25, le=200)
    body_shape: str | None = Field(default=None, max_length=40)
    skin_tone: str | None = Field(default=None, max_length=40)
    hair_tone: str | None = Field(default=None, max_length=40)
    style_keywords: list[str] = Field(default_factory=list, max_length=12)


class StyleProfileView(StyleProfileUpdate):
    display_name: str = "Style User"
    feature_metrics: list[FeatureMetric] = Field(default_factory=list)


class ProfileView(BaseModel):
    user: PublicUser | None
    style_profile: StyleProfileView


class FeatureSummary(BaseModel):
    score: float = Field(ge=0, le=1)
    title: str
    summary: str


class HomeRecommendation(BaseModel):
    recommendation_id: str
    title: str
    scene: Scene
    score: float = Field(ge=0, le=1)
    image_url: str | None = None
    source_task_id: str | None = None


class TodaySuggestion(BaseModel):
    title: str
    body: str


class HomeView(BaseModel):
    feature_summary: FeatureSummary
    recommendations: list[HomeRecommendation]
    today_suggestion: TodaySuggestion
    backend_status: dict[str, Any]


class InspirationLook(BaseModel):
    inspiration_id: str
    title: str
    scene: Scene
    palette: str
    note: str
    score: float = Field(ge=0, le=1)
    image_url: str | None = None
    favorite_id: str | None = None


class InspirationPage(BaseModel):
    items: list[InspirationLook]
    next_cursor: str | None = None


class FavoriteType(StrEnum):
    outfit = "outfit"
    item = "item"
    inspiration = "inspiration"


class FavoriteCreate(BaseModel):
    favorite_type: FavoriteType
    target_id: str = Field(min_length=1, max_length=160)
    snapshot: dict[str, Any] = Field(default_factory=dict)


class FavoriteView(FavoriteCreate):
    favorite_id: str
    owner_id: str | None = None
