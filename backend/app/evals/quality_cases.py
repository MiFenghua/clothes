from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class QualityCase:
    case_id: str
    description: str
    expected_status: str
    minimum_recommendation_score: float | None = None
    minimum_image_score: float | None = None


RECOMMENDATION_EVAL_CASES = [
    QualityCase(
        case_id="daily_clean_budget",
        description="日常、干净、300-800 预算应输出完整高可信搭配。",
        expected_status="succeeded",
        minimum_recommendation_score=0.82,
        minimum_image_score=0.84,
    ),
    QualityCase(
        case_id="avoid_conflict",
        description="商品命中明确避雷项时必须拒绝硬凑。",
        expected_status="failed",
    ),
    QualityCase(
        case_id="image_qc_partial",
        description="推荐可信但图像低质时返回 partial_succeeded，不展示低质图。",
        expected_status="partial_succeeded",
        minimum_recommendation_score=0.82,
    ),
]

