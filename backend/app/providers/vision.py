from __future__ import annotations

import asyncio
import base64
import json
import re
from pathlib import Path
from typing import Protocol

from pydantic import BaseModel, Field

from app.config import Settings
from app.schemas.domain import PhotoQuality, StyleProfile, StyleTaskRequest
from app.schemas.quality import ImageCandidate


class PhotoProfileProvider(Protocol):
    async def analyze(self, *, task_id: str, request: StyleTaskRequest) -> StyleProfile:
        ...


class ImageQualityScoringProvider(Protocol):
    async def score_candidates(
        self,
        *,
        task_id: str,
        request: StyleTaskRequest,
        candidates: list[ImageCandidate],
        product_image_urls: list[str],
    ) -> dict[str, dict[str, float]]:
        ...


class ImageQualityScores(BaseModel):
    identity_score: float = Field(ge=0, le=1)
    garment_score: float = Field(ge=0, le=1)
    artifact_score: float = Field(ge=0, le=1)
    realism_score: float = Field(ge=0, le=1)


class ArkVisionClient:
    def __init__(self, settings: Settings) -> None:
        if not settings.ark_api_key:
            raise RuntimeError("STYLE_BACKEND_ARK_API_KEY is required for Ark vision providers")
        try:
            from openai import OpenAI
        except Exception as exc:  # pragma: no cover - optional production dependency
            raise RuntimeError("openai is required for Ark vision providers") from exc
        self.settings = settings
        self.client = OpenAI(api_key=settings.ark_api_key, base_url=settings.ark_base_url)

    async def create_json(self, *, prompt: str, image_urls: list[str]) -> dict:
        content: list[dict] = [{"type": "text", "text": prompt}]
        for url in image_urls:
            content.append({"type": "image_url", "image_url": {"url": url}})

        response = await asyncio.to_thread(
            self.client.chat.completions.create,
            model=self.settings.ark_vision_model,
            messages=[{"role": "user", "content": content}],
            temperature=0.1,
        )
        text = response.choices[0].message.content or ""
        return _parse_json(text)

    def local_or_remote_image(self, request: StyleTaskRequest) -> str:
        local_path = self.settings.storage_dir / request.photo_object_key
        if local_path.exists():
            return _file_to_data_url(local_path)
        return request.photo_url


class ArkPhotoProfileProvider(PhotoProfileProvider):
    def __init__(self, settings: Settings) -> None:
        self.vision = ArkVisionClient(settings)

    async def analyze(self, *, task_id: str, request: StyleTaskRequest) -> StyleProfile:
        payload = await self.vision.create_json(
            prompt=self._prompt(request),
            image_urls=[self.vision.local_or_remote_image(request)],
        )
        profile = StyleProfile.model_validate(payload)
        return profile.model_copy(update={"summary": profile.summary[:120]})

    def _prompt(self, request: StyleTaskRequest) -> str:
        preferences = request.preferences
        budget_min = request.budget.min if request.budget.min is not None else "未填"
        budget_max = request.budget.max if request.budget.max is not None else "未填"
        return f"""你是一名专业但克制的女性穿搭顾问，只分析照片中与穿搭相关的信息。
不要推断民族、身份、健康、收入或未填写的年龄；不要评价身材好坏；不要输出 Markdown。

用户输入：
- 场景：{request.scene.value}
- 预算：{budget_min}-{budget_max}
- 年龄：{preferences.age_years if preferences.age_years is not None else "未填"}
- 身高：{preferences.height_cm if preferences.height_cm is not None else "未填"}
- 常穿尺码：{preferences.usual_size or "未填"}
- 喜欢风格：{preferences.liked_style or "未填"}
- 避雷项：{preferences.avoid or "未填"}

请输出严格 JSON：
{{
  "body_proportion": "petite | balanced | tall | curvy | straight",
  "undertone": "warm | cool | neutral",
  "hair_tone": "dark | brown | light | red | covered",
  "style_signals": ["中文风格关键词，如 干净、轻熟、温柔"],
  "fit_advice": ["中文版型建议，如 高腰线、收腰、线条干净"],
  "palette": ["ivory", "denim", "black"],
  "photo_quality": {{
    "is_full_body": true,
    "face_visible": true,
    "lighting": "poor | fair | good",
    "occlusion": "low | medium | high",
    "resolution_score": 0.0
  }},
  "confidence": 0.0,
  "summary": "不超过120字中文总结"
}}"""


class ArkImageQualityScoringProvider(ImageQualityScoringProvider):
    def __init__(self, settings: Settings) -> None:
        self.vision = ArkVisionClient(settings)

    async def score_candidates(
        self,
        *,
        task_id: str,
        request: StyleTaskRequest,
        candidates: list[ImageCandidate],
        product_image_urls: list[str],
    ) -> dict[str, dict[str, float]]:
        scores: dict[str, dict[str, float]] = {}
        user_photo = self.vision.local_or_remote_image(request)
        product_refs = product_image_urls[:6]
        for candidate in candidates:
            payload = await self.vision.create_json(
                prompt=self._prompt(candidate),
                image_urls=[user_photo, candidate.image_url, *product_refs],
            )
            parsed = ImageQualityScores.model_validate(payload)
            scores[candidate.candidate_id] = parsed.model_dump()
        return scores

    def _prompt(self, candidate: ImageCandidate) -> str:
        return f"""你是 AI 试穿图质检员。
输入图片顺序：1 用户原始全身照；2 待质检试穿图；3 之后为入选商品主图。
请只输出严格 JSON，不要输出解释。

评分维度：
- identity_score：试穿图是否保留本人脸部、肤色、发型、体态比例。
- garment_score：衣物品类、主色、廓形、材质是否贴近商品图。
- artifact_score：是否没有多余人物、肢体变形、文字水印、严重遮挡或低清晰度。
- realism_score：整体光线、姿态、服装贴合和真实感。

候选图 ID：{candidate.candidate_id}
输出：
{{
  "identity_score": 0.0,
  "garment_score": 0.0,
  "artifact_score": 0.0,
  "realism_score": 0.0
}}"""


def _parse_json(text: str) -> dict:
    stripped = text.strip()
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        match = re.search(r"```(?:json)?\s*([\s\S]*?)```", stripped, re.I) or re.search(r"(\{[\s\S]*\})", stripped)
        if not match:
            raise
        return json.loads(match.group(1))


def _file_to_data_url(path: Path) -> str:
    mime = {
        ".png": "image/png",
        ".webp": "image/webp",
        ".gif": "image/gif",
    }.get(path.suffix.lower(), "image/jpeg")
    data = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{data}"
