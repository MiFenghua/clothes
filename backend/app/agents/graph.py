from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from app.agents.fashion_director import FashionDirectorAgent
from app.agents.fit_critic import FitCriticAgent
from app.agents.image_prompt import ImagePromptAgent
from app.agents.image_qc_judge import ImageQCJudgeAgent
from app.agents.photo_profiler import PhotoProfilerAgent
from app.agents.preference_resolver import PreferenceResolverAgent
from app.agents.product_normalizer import ProductNormalizerAgent
from app.agents.product_scout import ProductScoutAgent
from app.agents.recovery import RecoveryAgent
from app.agents.state import StyleGraphState
from app.agents.stylist_composer import StylistComposerAgent
from app.agents.tryon_generator import TryOnGeneratorAgent
from app.config import Settings
from app.providers.image import TryOnImageProvider
from app.providers.outfit_planner import OutfitPlanner
from app.providers.query_planner import SearchQueryPlanner
from app.providers.search import ProductSearchProvider
from app.providers.tracing import TraceRecorder
from app.providers.vision import ImageQualityScoringProvider, PhotoProfileProvider
from app.schemas.domain import OutfitCandidate, ProductCandidate, StyleTaskRequest, TaskStatus
from app.schemas.quality import RecommendationReport
from app.schemas.results import StyleTaskResult

StatusCallback = Callable[[TaskStatus, str, int], Awaitable[None] | None]


@dataclass(frozen=True)
class GraphManifest:
    nodes: list[str]
    edges: list[tuple[str, str]]


class StyleAgentGraph:
    """Explicit agent graph.

    This class is intentionally framework-neutral. Production can wrap these same nodes with
    LangGraph StateGraph while Temporal owns workflow durability.
    """

    def __init__(
        self,
        *,
        settings: Settings,
        tracer: TraceRecorder,
        search_provider: ProductSearchProvider,
        image_provider: TryOnImageProvider,
        photo_provider: PhotoProfileProvider | None = None,
        query_planner: SearchQueryPlanner | None = None,
        outfit_planner: OutfitPlanner | None = None,
        image_quality_provider: ImageQualityScoringProvider | None = None,
        wardrobe_products: Callable[[list[str]], list[ProductCandidate]] | None = None,
    ) -> None:
        self.settings = settings
        self.tracer = tracer
        self.photo_profiler = PhotoProfilerAgent(
            tracer,
            photo_provider,
        )
        self.preference_resolver = PreferenceResolverAgent(tracer)
        self.product_scout = ProductScoutAgent(
            tracer,
            search_provider,
            query_planner=query_planner,
            wardrobe_products=wardrobe_products,
        )
        self.product_normalizer = ProductNormalizerAgent(tracer)
        self.stylist_composer = StylistComposerAgent(tracer, outfit_planner)
        self.fit_critic = FitCriticAgent(tracer, settings.recommendation_threshold)
        self.fashion_director = FashionDirectorAgent(tracer, settings.recommendation_threshold)
        self.image_prompt = ImagePromptAgent(tracer)
        self.tryon_generator = TryOnGeneratorAgent(tracer, image_provider)
        self.image_qc = ImageQCJudgeAgent(tracer, settings.image_threshold, image_quality_provider)
        self.recovery = RecoveryAgent(tracer)

    def manifest(self) -> GraphManifest:
        nodes = [
            "PhotoProfilerAgent",
            "PreferenceResolverAgent",
            "ProductScoutAgent",
            "ProductNormalizerAgent",
            "StylistComposerAgent",
            "FitCriticAgent",
            "FashionDirectorAgent",
            "ImagePromptAgent",
            "TryOnGeneratorAgent",
            "ImageQCJudgeAgent",
            "RecoveryAgent",
        ]
        return GraphManifest(nodes=nodes, edges=list(zip(nodes, nodes[1:])))

    async def run(
        self,
        *,
        task_id: str,
        request: StyleTaskRequest,
        status_callback: StatusCallback | None = None,
    ) -> StyleTaskResult:
        state = StyleGraphState(task_id=task_id, request=request)
        await self._status(status_callback, TaskStatus.profiling_photo, "正在分析照片质量、比例和风格线索", 10)
        state = await self.photo_profiler.run(state)

        if state.profile and (not state.profile.photo_quality.is_full_body or state.profile.confidence < 0.55):
            state = state.model_copy(update={"blocking_reason": "照片质量不足，请上传清晰、完整、无遮挡的全身照。"})
            return await self.recovery.build_result(state)

        await self._status(status_callback, TaskStatus.resolving_preferences, "正在融合场景、偏好、预算和衣橱约束", 18)
        state = await self.preference_resolver.run(state)

        await self._status(status_callback, TaskStatus.scouting_products, "正在多市场检索真实商品详情和主图", 32)
        state = await self.product_scout.run(state)

        await self._status(status_callback, TaskStatus.normalizing_products, "正在清洗商品、尺码、价格和来源可信度", 46)
        state = await self.product_normalizer.run(state)

        await self._status(status_callback, TaskStatus.composing_outfits, "正在组合多套候选穿搭", 58)
        state = await self.stylist_composer.run(state)

        await self._status(status_callback, TaskStatus.reviewing_outfits, "正在用穿搭质量闸门审核候选方案", 68)
        state = await self.fit_critic.run(state)

        await self._status(status_callback, TaskStatus.directing_fashion, "正在选择最终推荐并生成解释报告", 74)
        state = await self.fashion_director.run(state)
        if state.blocking_reason:
            return await self.recovery.build_result(state)

        state = await self._run_image_generation(state, status_callback=status_callback, base_progress=80)

        result = await self.recovery.build_result(state)
        await self._status(
            status_callback,
            result.status,
            result.user_message or ("搭配完成" if result.status == TaskStatus.succeeded else "任务结束"),
            100,
        )
        return result

    async def retry_image(
        self,
        *,
        task_id: str,
        request: StyleTaskRequest,
        outfit: OutfitCandidate,
        recommendation_report: RecommendationReport | None,
        rejected_outfits: list[OutfitCandidate],
        status_callback: StatusCallback | None = None,
    ) -> StyleTaskResult:
        state = StyleGraphState(
            task_id=task_id,
            request=request,
            selected_outfit=outfit,
            recommendation_report=recommendation_report,
            rejected_outfits=rejected_outfits,
        )
        state = await self._run_image_generation(state, status_callback=status_callback, base_progress=76)
        result = await self.recovery.build_result(state)
        await self._status(
            status_callback,
            result.status,
            result.user_message or ("试穿图已重新生成" if result.try_on_image_url else "试穿图重试结束"),
            100,
        )
        return result

    async def _run_image_generation(
        self,
        state: StyleGraphState,
        *,
        status_callback: StatusCallback | None,
        base_progress: int,
    ) -> StyleGraphState:
        await self._status(status_callback, TaskStatus.generating_candidates, "正在构建高质量试穿图提示词", base_progress)
        state = await self.image_prompt.run(state)

        for attempt in range(self.settings.max_image_attempts):
            status = TaskStatus.generating_candidates if attempt == 0 else TaskStatus.retrying_image_generation
            progress = min(96, base_progress + 4 + attempt * 7)
            await self._status(status_callback, status, f"正在生成第 {attempt + 1} 轮试穿图候选", progress)
            before_count = len(state.image_candidates)
            state = await self.tryon_generator.run(
                state,
                attempt=attempt,
                count=self.settings.image_candidates_per_attempt,
            )
            new_candidates = state.image_candidates[before_count:]
            await self._status(
                status_callback,
                TaskStatus.checking_image_quality,
                f"正在质检第 {attempt + 1} 轮试穿图的人物相似度、衣物还原和画面瑕疵",
                min(98, progress + 3),
            )
            state = await self.image_qc.run(state, candidates=new_candidates)
            if state.accepted_image:
                break
            if state.image_prompt and state.image_quality_reports:
                best_failed = state.image_quality_reports[0]
                state = state.model_copy(
                    update={"image_prompt": f"{state.image_prompt}\n\nCorrection note: {best_failed.retry_prompt_hint}"}
                )
        return state

    async def _status(
        self,
        callback: StatusCallback | None,
        status: TaskStatus,
        message: str,
        progress: int,
    ) -> None:
        if callback is None:
            return
        maybe_awaitable = callback(status, message, progress)
        if maybe_awaitable is not None:
            await maybe_awaitable

    def build_langgraph(self) -> Any:
        """Optional LangGraph adapter.

        The dependency is intentionally loaded lazily so local core tests can run without
        requiring a full agent runtime. Production code can call this method after installing
        `langgraph`.
        """
        try:
            from langgraph.graph import END, StateGraph
        except Exception as exc:  # pragma: no cover - depends on optional runtime
            raise RuntimeError("langgraph is not installed") from exc

        graph = StateGraph(dict)
        manifest = self.manifest()
        for node in manifest.nodes:
            graph.add_node(node, lambda state: state)
        for left, right in manifest.edges:
            graph.add_edge(left, right)
        graph.add_edge(manifest.nodes[-1], END)
        graph.set_entry_point(manifest.nodes[0])
        return graph.compile()
