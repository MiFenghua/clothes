from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class GateStatus(StrEnum):
    passed = "passed"
    failed = "failed"
    warning = "warning"


class QualityGateReport(BaseModel):
    gate: str
    status: GateStatus
    score: float = Field(ge=0, le=1)
    reasons: list[str] = Field(default_factory=list)
    blocking: bool = False


class RecommendationReport(BaseModel):
    final_score: float = Field(ge=0, le=1)
    fit_score: float = Field(ge=0, le=1)
    color_score: float = Field(ge=0, le=1)
    occasion_score: float = Field(ge=0, le=1)
    budget_score: float = Field(ge=0, le=1)
    wardrobe_score: float = Field(ge=0, le=1)
    gates: list[QualityGateReport]
    risk_flags: list[str] = Field(default_factory=list)
    why_this_works: list[str] = Field(default_factory=list)
    why_not_others: list[str] = Field(default_factory=list)


class ImageCandidate(BaseModel):
    candidate_id: str
    image_url: str
    prompt: str
    provider: str
    attempt: int
    metadata: dict[str, float | str | bool] = Field(default_factory=dict)


class ImageQualityReport(BaseModel):
    candidate_id: str
    overall_score: float = Field(ge=0, le=1)
    identity_score: float = Field(ge=0, le=1)
    garment_score: float = Field(ge=0, le=1)
    artifact_score: float = Field(ge=0, le=1)
    realism_score: float = Field(ge=0, le=1)
    gates: list[QualityGateReport]
    accepted: bool
    retry_prompt_hint: str | None = None

