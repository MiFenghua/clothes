from __future__ import annotations

from app.agents.quality_gates import image_quality_gates
from app.agents.state import StyleGraphState
from app.providers.tracing import TraceRecorder
from app.providers.vision import ImageQualityScoringProvider
from app.schemas.quality import ImageCandidate


class ImageQCJudgeAgent:
    node_name = "ImageQCJudgeAgent"

    def __init__(
        self,
        tracer: TraceRecorder,
        threshold: float,
        scoring_provider: ImageQualityScoringProvider | None = None,
    ) -> None:
        self.tracer = tracer
        self.threshold = threshold
        self.scoring_provider = scoring_provider

    async def run(self, state: StyleGraphState, *, candidates: list[ImageCandidate]) -> StyleGraphState:
        candidates = await self._enrich_with_external_scores(state, candidates)
        reports = []
        for candidate in candidates:
            reports.append(
                image_quality_gates(
                    candidate_id=candidate.candidate_id,
                    identity_score=float(candidate.metadata.get("identity_score", 0)),
                    garment_score=float(candidate.metadata.get("garment_score", 0)),
                    artifact_score=float(candidate.metadata.get("artifact_score", 0)),
                    realism_score=float(candidate.metadata.get("realism_score", 0)),
                    threshold=self.threshold,
                )
            )
        reports.sort(key=lambda report: report.overall_score, reverse=True)
        accepted_report = next((report for report in reports if report.accepted), None)
        accepted_candidate = None
        if accepted_report:
            accepted_candidate = next(candidate for candidate in candidates if candidate.candidate_id == accepted_report.candidate_id)
        self.tracer.record(
            state.task_id,
            self.node_name,
            "image_quality_checked",
            {"reports": [report.model_dump() for report in reports], "accepted": accepted_report.candidate_id if accepted_report else None},
        )
        return state.model_copy(
            update={
                "image_quality_reports": [*state.image_quality_reports, *reports],
                "accepted_image": accepted_candidate or state.accepted_image,
            }
        )

    async def _enrich_with_external_scores(
        self,
        state: StyleGraphState,
        candidates: list[ImageCandidate],
    ) -> list[ImageCandidate]:
        if self.scoring_provider is None or state.selected_outfit is None:
            return candidates
        try:
            scores = await self.scoring_provider.score_candidates(
                task_id=state.task_id,
                request=state.request,
                candidates=candidates,
                product_image_urls=[item.image_url for item in state.selected_outfit.items],
            )
        except Exception as exc:
            self.tracer.record(state.task_id, self.node_name, "external_image_qc_failed", {"error": str(exc)})
            return candidates

        enriched = []
        for candidate in candidates:
            metadata = {**candidate.metadata, **scores.get(candidate.candidate_id, {})}
            enriched.append(candidate.model_copy(update={"metadata": metadata}))
        return enriched
