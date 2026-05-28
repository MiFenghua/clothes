from __future__ import annotations

from functools import lru_cache
from pathlib import Path

try:
    from pydantic_settings import BaseSettings, SettingsConfigDict
except Exception:  # pragma: no cover - imported only when dependencies are absent
    BaseSettings = object  # type: ignore[misc,assignment]
    SettingsConfigDict = dict  # type: ignore[assignment]

BACKEND_ROOT = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    app_name: str = "clothes-agent-backend"
    public_base_url: str = "http://127.0.0.1:8000"
    storage_dir: Path = BACKEND_ROOT / "storage"
    generated_dir: Path = BACKEND_ROOT / "storage/generated"
    upload_dir: Path = BACKEND_ROOT / "storage/uploads"
    postgres_dsn: str | None = None
    object_store_bucket: str | None = None
    google_client_id: str | None = None
    auth_store_path: Path = BACKEND_ROOT / "storage/auth-store.json"
    product_store_path: Path = BACKEND_ROOT / "storage/product-store.json"
    auth_session_max_age_days: int = 30
    temporal_address: str = "127.0.0.1:7233"
    temporal_task_queue: str = "clothes-style-tasks"
    search_provider: str = "taobao_union"
    image_provider: str = "ark"
    model_provider: str = "ark"
    recommendation_threshold: float = 0.82
    image_threshold: float = 0.84
    max_image_attempts: int = 2
    image_candidates_per_attempt: int = 3
    image_generation_concurrency: int = 3
    image_quality_concurrency: int = 3
    ark_api_key: str | None = None
    ark_base_url: str = "https://ark.cn-beijing.volces.com/api/v3"
    ark_vision_model: str = "doubao-seed-1-6-vision-250815"
    ark_image_model: str = "doubao-seedream-5-0-260128"
    ark_image_size: str = "2K"
    ark_watermark: bool = True
    taobao_union_endpoint: str = "https://eco.taobao.com/router/rest"
    taobao_union_method: str = "taobao.tbk.dg.material.optional.upgrade"
    taobao_union_app_key: str | None = None
    taobao_union_app_secret: str | None = None
    taobao_union_adzone_id: str | None = None
    taobao_union_site_id: str | None = None
    taobao_union_material_id: int = 80309
    taobao_union_sign_method: str = "md5"
    taobao_union_timeout_seconds: int = 15

    model_config = SettingsConfigDict(env_prefix="STYLE_BACKEND_", env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
