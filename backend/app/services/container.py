from __future__ import annotations

import os
from functools import lru_cache

from app.agents.graph import StyleAgentGraph
from app.config import get_settings
from app.providers.auth import AuthStore
from app.providers.google_auth import GoogleOAuthIdTokenVerifier
from app.providers.image import ArkSeedreamImageProvider, LocalTryOnImageProvider, TryOnImageProvider
from app.providers.persistence import (
    FavoritesRepository,
    InMemoryFavoritesRepository,
    InMemoryWardrobeRepository,
    TaskRepository,
    WardrobeRepository,
)
from app.providers.postgres import (
    PostgresAuthStore,
    PostgresDatabase,
    PostgresFavoritesRepository,
    PostgresTaskRepository,
    PostgresTraceRecorder,
    PostgresWardrobeRepository,
)
from app.providers.product_content import FavoriteRepository, InspirationRepository, ProductContentStore, ProfileRepository
from app.providers.query_planner import ArkSearchQueryPlanner, SearchQueryPlanner
from app.providers.search import (
    CompositeProductSearchProvider,
    LocalDemoSearchProvider,
    ProductSearchProvider,
    TaobaoUnionProductSearchProvider,
)
from app.providers.storage import LocalObjectStorage
from app.providers.tracing import InMemoryTraceRecorder, TraceRecorder
from app.providers.vision import (
    ArkImageQualityScoringProvider,
    ArkPhotoProfileProvider,
    ImageQualityScoringProvider,
    PhotoProfileProvider,
)
from app.services.task_service import TaskService, create_task_service


class AppContainer:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.storage = LocalObjectStorage(self.settings)
        self.postgres_database: PostgresDatabase | None = (
            PostgresDatabase(self.settings.postgres_dsn) if self.settings.postgres_dsn else None
        )
        self.tracer: TraceRecorder
        self.auth_store: AuthStore | PostgresAuthStore
        self.wardrobe_repository: WardrobeRepository
        self.task_repository: TaskRepository | None
        self.favorites_repository: FavoritesRepository
        if self.postgres_database is not None:
            if not self.postgres_database.check_connection():
                raise RuntimeError("Postgres connection check failed")
            self.tracer = PostgresTraceRecorder(self.postgres_database)
            self.auth_store = PostgresAuthStore(
                self.postgres_database,
                session_max_age_days=self.settings.auth_session_max_age_days,
            )
            self.wardrobe_repository = PostgresWardrobeRepository(self.postgres_database)
            self.task_repository = PostgresTaskRepository(self.postgres_database)
            self.favorites_repository = PostgresFavoritesRepository(self.postgres_database)
        else:
            self.tracer = InMemoryTraceRecorder()
            self.auth_store = AuthStore(
                self.settings.auth_store_path,
                session_max_age_days=self.settings.auth_session_max_age_days,
            )
            self.wardrobe_repository = InMemoryWardrobeRepository()
            self.task_repository = None
            self.favorites_repository = InMemoryFavoritesRepository()
        self.google_id_token_verifier = GoogleOAuthIdTokenVerifier(self.settings.google_client_id)
        self.photo_provider = self._create_photo_provider()
        self.query_planner = self._create_query_planner()
        self.search_provider = self._create_search_provider()
        self.image_provider = self._create_image_provider()
        self.image_quality_provider = self._create_image_quality_provider()
        self.product_store = ProductContentStore(self.settings.product_store_path)
        self.profile_repository = ProfileRepository(self.product_store)
        self.favorite_repository = FavoriteRepository(self.product_store)
        self.inspiration_repository = InspirationRepository()
        self.graph = StyleAgentGraph(
            settings=self.settings,
            tracer=self.tracer,
            search_provider=self.search_provider,
            image_provider=self.image_provider,
            photo_provider=self.photo_provider,
            query_planner=self.query_planner,
            image_quality_provider=self.image_quality_provider,
            wardrobe_products=self.wardrobe_repository.products_for_ids,
        )
        self.task_service: TaskService = create_task_service(
            self.graph,
            self.tracer,
            wardrobe_repository=self.wardrobe_repository,
            favorites_repository=self.favorites_repository,
            repository=self.task_repository,
        )

    def _create_photo_provider(self) -> PhotoProfileProvider | None:
        if self.settings.model_provider == "ark" and self.settings.ark_api_key:
            return ArkPhotoProfileProvider(self.settings)
        return None

    def _create_search_provider(self) -> ProductSearchProvider:
        provider_names = [name.strip() for name in self.settings.search_provider.split(",") if name.strip()]
        if not provider_names:
            provider_names = ["taobao_union"]

        providers: list[ProductSearchProvider] = []
        for name in provider_names:
            if name in {"taobao_union", "taobao", "tbk"}:
                if not self._taobao_union_configured() and os.getenv("STYLE_BACKEND_SEARCH_PROVIDER") is None:
                    providers.append(LocalDemoSearchProvider())
                    continue
                providers.append(TaobaoUnionProductSearchProvider(self.settings))
            elif name in {"local", "local_demo"}:
                providers.append(LocalDemoSearchProvider())
            else:
                raise RuntimeError(f"Unsupported STYLE_BACKEND_SEARCH_PROVIDER: {name}")

        if len(providers) == 1:
            return providers[0]
        return CompositeProductSearchProvider(providers)

    def _taobao_union_configured(self) -> bool:
        return bool(
            self.settings.taobao_union_app_key
            and self.settings.taobao_union_app_secret
            and self.settings.taobao_union_adzone_id
        )

    def _create_query_planner(self) -> SearchQueryPlanner | None:
        if self.settings.model_provider == "ark" and self.settings.ark_api_key:
            return ArkSearchQueryPlanner(self.settings)
        return None

    def _create_image_provider(self) -> TryOnImageProvider:
        if self.settings.image_provider == "ark" and self.settings.ark_api_key:
            return ArkSeedreamImageProvider(self.settings)
        return LocalTryOnImageProvider()

    def _create_image_quality_provider(self) -> ImageQualityScoringProvider | None:
        if self.settings.model_provider == "ark" and self.settings.ark_api_key:
            return ArkImageQualityScoringProvider(self.settings)
        return None


@lru_cache
def get_container() -> AppContainer:
    return AppContainer()
