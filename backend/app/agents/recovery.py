from __future__ import annotations

from app.agents.state import StyleGraphState
from app.providers.tracing import TraceRecorder
from app.schemas.domain import TaskStatus
from app.schemas.results import StyleTaskResult


class RecoveryAgent:
    node_name = "RecoveryAgent"

    def __init__(self, tracer: TraceRecorder) -> None:
        self.tracer = tracer

    async def build_result(self, state: StyleGraphState) -> StyleTaskResult:
        if state.blocking_reason:
            self.tracer.record(state.task_id, self.node_name, "failed_without_outfit", {"reason": state.blocking_reason})
            return StyleTaskResult(
                task_id=state.task_id,
                status=TaskStatus.failed,
                outfit=None,
                recommendation_report=state.recommendation_report,
                user_message=state.blocking_reason,
                alternatives_rejected=state.rejected_outfits,
            )
        if state.selected_outfit and not state.accepted_image:
            message = "推荐方案已通过质量审核，但试穿图未通过本人真实感/衣物还原质检，暂不展示低质图。"
            self.tracer.record(state.task_id, self.node_name, "partial_result", {"message": message})
            return StyleTaskResult(
                task_id=state.task_id,
                status=TaskStatus.partial_succeeded,
                outfit=state.selected_outfit,
                recommendation_report=state.recommendation_report,
                image_quality_report=state.image_quality_reports[0] if state.image_quality_reports else None,
                alternatives_rejected=state.rejected_outfits,
                user_message=message,
            )
        if state.selected_outfit and state.accepted_image:
            best_report = next(
                report for report in state.image_quality_reports if report.candidate_id == state.accepted_image.candidate_id
            )
            return StyleTaskResult(
                task_id=state.task_id,
                status=TaskStatus.succeeded,
                outfit=state.selected_outfit,
                try_on_image_url=state.accepted_image.image_url,
                recommendation_report=state.recommendation_report,
                image_quality_report=best_report,
                alternatives_rejected=state.rejected_outfits,
                user_message="搭配和试穿图均已通过质量审核。",
            )
        return StyleTaskResult(task_id=state.task_id, status=TaskStatus.failed, user_message="任务未生成可用结果。")
