from __future__ import annotations

import re

from app.schemas.domain import Marketplace, OutfitCandidate, OutfitItem, ProductCandidate
from app.schemas.quality import GateStatus, ImageQualityReport, QualityGateReport, RecommendationReport


DETAIL_PATTERNS: dict[Marketplace, list[re.Pattern[str]]] = {
    Marketplace.taobao: [re.compile(r"^https://item\.taobao\.com/item\.htm", re.I)],
    Marketplace.tmall: [re.compile(r"^https://detail\.tmall\.com/item\.htm", re.I)],
    Marketplace.amazon: [
        re.compile(r"^https://[^/]*amazon\.[^/]+/dp/[A-Z0-9]{10}(?:[/?]|$)", re.I),
        re.compile(r"^https://[^/]*amazon\.[^/]+/gp/product/[A-Z0-9]{10}(?:[/?]|$)", re.I),
    ],
    Marketplace.jd: [re.compile(r"^https://item\.jd\.com/.+\.html", re.I)],
    Marketplace.pdd: [re.compile(r"^https://mobile\.yangkeduo\.com/goods\.html", re.I)],
    Marketplace.owned: [re.compile(r"^owned://wardrobe/", re.I), re.compile(r"^https?://", re.I)],
}

BLOCKED_IMAGE_PATTERNS = ["favicon.ico", "logo", "placeholder", "base64,"]


def is_detail_product(product: ProductCandidate | OutfitItem) -> bool:
    return any(pattern.search(product.product_url) for pattern in DETAIL_PATTERNS.get(product.marketplace, []))


def has_usable_image(product: ProductCandidate | OutfitItem) -> bool:
    return bool(product.image_url) and not any(pattern in product.image_url.lower() for pattern in BLOCKED_IMAGE_PATTERNS)


def data_gate_for_product(product: ProductCandidate | OutfitItem) -> QualityGateReport:
    reasons: list[str] = []
    score = product.source_reliability
    if not is_detail_product(product):
        reasons.append("商品不是可信详情页链接")
        score -= 0.35
    if not has_usable_image(product):
        reasons.append("商品缺少可用于试穿的主图")
        score -= 0.35
    if product.category not in {"bag", "accessory"} and not product.sizes and product.marketplace != Marketplace.owned:
        reasons.append("商品尺码信息不足")
        score -= 0.12
    if product.risk_flags:
        reasons.extend(product.risk_flags)
        score -= 0.08 * len(product.risk_flags)
    score = max(0, min(1, score))
    return QualityGateReport(
        gate=f"data:{product.product_id}",
        status=GateStatus.passed if score >= 0.72 and not reasons[:2] else GateStatus.failed,
        score=score,
        reasons=reasons or ["商品详情、图片和尺码数据可用"],
        blocking=score < 0.72 or any("详情页" in reason or "主图" in reason for reason in reasons),
    )


def data_gate_for_outfit(outfit: OutfitCandidate) -> QualityGateReport:
    item_reports = [data_gate_for_product(item) for item in outfit.items]
    score = min(report.score for report in item_reports) if item_reports else 0
    blocking_reports = [report for report in item_reports if report.blocking]
    return QualityGateReport(
        gate="Data Gate",
        status=GateStatus.failed if blocking_reports else GateStatus.passed,
        score=score,
        reasons=[reason for report in item_reports for reason in report.reasons],
        blocking=bool(blocking_reports),
    )


def styling_gate(report: RecommendationReport, threshold: float) -> QualityGateReport:
    severe_risks = [risk for risk in report.risk_flags if risk.startswith("severe:")]
    passed = report.final_score >= threshold and not severe_risks
    return QualityGateReport(
        gate="Styling Gate",
        status=GateStatus.passed if passed else GateStatus.failed,
        score=report.final_score,
        reasons=report.why_this_works if passed else severe_risks or ["搭配综合分未达到质量阈值"],
        blocking=not passed,
    )


def explanation_gate(outfit: OutfitCandidate) -> QualityGateReport:
    missing_item_reason = [item.product_id for item in outfit.items if not item.match_reason or not item.selection_reason]
    enough_outfit_reason = len(outfit.why_this_works) >= 2
    passed = not missing_item_reason and enough_outfit_reason
    return QualityGateReport(
        gate="Explanation Gate",
        status=GateStatus.passed if passed else GateStatus.failed,
        score=1 if passed else 0.45,
        reasons=outfit.why_this_works if passed else [f"缺少可解释理由: {', '.join(missing_item_reason)}"],
        blocking=not passed,
    )


def image_quality_gates(
    *,
    candidate_id: str,
    identity_score: float,
    garment_score: float,
    artifact_score: float,
    realism_score: float,
    threshold: float,
) -> ImageQualityReport:
    gates = [
        QualityGateReport(
            gate="Identity Gate",
            status=GateStatus.passed if identity_score >= 0.86 else GateStatus.failed,
            score=identity_score,
            reasons=["人物脸部、肤色、体态和比例接近原图"] if identity_score >= 0.86 else ["人物真实感或本人相似度不足"],
            blocking=identity_score < 0.86,
        ),
        QualityGateReport(
            gate="Garment Gate",
            status=GateStatus.passed if garment_score >= 0.78 else GateStatus.failed,
            score=garment_score,
            reasons=["衣物品类、主色和廓形匹配商品图"] if garment_score >= 0.78 else ["衣物还原度不足"],
            blocking=garment_score < 0.78,
        ),
        QualityGateReport(
            gate="Artifact Gate",
            status=GateStatus.passed if artifact_score >= 0.9 else GateStatus.failed,
            score=artifact_score,
            reasons=["未发现明显肢体异常、文字、水印或多余人物"] if artifact_score >= 0.9 else ["存在变形、遮挡或生成瑕疵风险"],
            blocking=artifact_score < 0.9,
        ),
    ]
    overall = round(identity_score * 0.4 + garment_score * 0.28 + artifact_score * 0.2 + realism_score * 0.12, 4)
    accepted = overall >= threshold and not any(gate.blocking for gate in gates)
    hint = None
    if not accepted:
        failed = [gate.gate for gate in gates if gate.blocking]
        hint = "；".join(failed) + " 未通过，请提高本人相似度、衣物还原和画面完整度。"
    return ImageQualityReport(
        candidate_id=candidate_id,
        overall_score=overall,
        identity_score=identity_score,
        garment_score=garment_score,
        artifact_score=artifact_score,
        realism_score=realism_score,
        gates=gates,
        accepted=accepted,
        retry_prompt_hint=hint,
    )

