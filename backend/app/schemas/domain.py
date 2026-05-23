from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, HttpUrl


class Scene(StrEnum):
    daily = "daily"
    commute = "commute"
    date = "date"
    travel = "travel"
    party = "party"


class Marketplace(StrEnum):
    taobao = "taobao"
    tmall = "tmall"
    jd = "jd"
    pdd = "pdd"
    amazon = "amazon"
    owned = "owned"


class ProductCategory(StrEnum):
    top = "top"
    bottom = "bottom"
    dress = "dress"
    outerwear = "outerwear"
    shoes = "shoes"
    bag = "bag"
    accessory = "accessory"


class TaskStatus(StrEnum):
    created = "created"
    profiling_photo = "profiling_photo"
    resolving_preferences = "resolving_preferences"
    scouting_products = "scouting_products"
    normalizing_products = "normalizing_products"
    composing_outfits = "composing_outfits"
    reviewing_outfits = "reviewing_outfits"
    directing_fashion = "directing_fashion"
    generating_candidates = "generating_candidates"
    checking_image_quality = "checking_image_quality"
    retrying_image_generation = "retrying_image_generation"
    partial_succeeded = "partial_succeeded"
    succeeded = "succeeded"
    failed = "failed"


class Budget(BaseModel):
    min: float | None = Field(default=None, ge=0)
    max: float | None = Field(default=None, ge=0)


class StylePreferences(BaseModel):
    liked_style: str | None = Field(default=None, max_length=160)
    avoid: str | None = Field(default=None, max_length=160)
    age_years: int | None = Field(default=None, ge=12, le=90)
    height_cm: int | None = Field(default=None, ge=100, le=230)
    weight_kg: int | None = Field(default=None, ge=25, le=200)
    usual_size: str | None = Field(default=None, max_length=40)


class StyleTaskRequest(BaseModel):
    photo_url: str
    photo_object_key: str
    scene: Scene = Scene.daily
    budget: Budget = Field(default_factory=lambda: Budget(min=300, max=800))
    preferences: StylePreferences = Field(default_factory=StylePreferences)
    wardrobe_item_ids: list[str] = Field(default_factory=list)
    marketplaces: list[Marketplace] = Field(
        default_factory=lambda: [
            Marketplace.taobao,
            Marketplace.tmall,
        ]
    )


class PhotoQuality(BaseModel):
    is_full_body: bool
    face_visible: bool
    lighting: str
    occlusion: str
    resolution_score: float = Field(ge=0, le=1)


class StyleProfile(BaseModel):
    body_proportion: str
    undertone: str
    hair_tone: str
    style_signals: list[str]
    fit_advice: list[str]
    palette: list[str]
    photo_quality: PhotoQuality
    confidence: float = Field(ge=0, le=1)
    summary: str


class PreferenceConstraints(BaseModel):
    scene: Scene
    budget: Budget
    positive_style_terms: list[str]
    negative_style_terms: list[str]
    required_fit_terms: list[str]
    palette: list[str]
    marketplaces: list[Marketplace]
    wardrobe_item_ids: list[str] = Field(default_factory=list)


class ProductCandidate(BaseModel):
    product_id: str
    marketplace: Marketplace
    source_provider: str | None = None
    category: ProductCategory
    title: str
    price: float = Field(ge=0)
    price_text: str | None = None
    image_url: str
    product_url: str
    shop_name: str | None = None
    sizes: list[str] = Field(default_factory=list)
    colors: list[str] = Field(default_factory=list)
    style_tags: list[str] = Field(default_factory=list)
    fit_tags: list[str] = Field(default_factory=list)
    source_reliability: float = Field(default=0.5, ge=0, le=1)
    score: float = Field(default=0, ge=0, le=1)
    risk_flags: list[str] = Field(default_factory=list)
    raw: dict[str, Any] = Field(default_factory=dict)


class OutfitItem(ProductCandidate):
    selection_reason: str
    match_reason: str
    selection_scores: dict[str, float] = Field(default_factory=dict)


class OutfitCandidate(BaseModel):
    candidate_id: str
    title: str
    items: list[OutfitItem]
    total_price: float
    score: float = Field(ge=0, le=1)
    score_breakdown: dict[str, float]
    why_this_works: list[str]
    why_not_others: list[str] = Field(default_factory=list)
    risk_flags: list[str] = Field(default_factory=list)


class WardrobeItem(BaseModel):
    item_id: str
    owner_id: str | None = None
    category: ProductCategory
    image_url: str | HttpUrl
    title: str
    colors: list[str] = Field(default_factory=list)
    style_tags: list[str] = Field(default_factory=list)
    fit_tags: list[str] = Field(default_factory=list)
    notes: str | None = None
