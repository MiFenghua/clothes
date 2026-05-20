from __future__ import annotations

from functools import lru_cache

from app.agents.graph import StyleAgentGraph
from app.config import get_settings
from app.providers.auth import AuthStore
from app.providers.google_auth import GoogleOAuthIdTokenVerifier
from app.providers.image import ArkSeedreamImageProvider, LocalTryOnImageProvider
from app.providers.persistence import InMemoryWardrobeRepository
from app.providers.product_content import FavoriteRepository, InspirationRepository, ProfileRepository
from app.providers.search import BrowserProductSearchProvider, LocalDemoSearchProvider
from app.providers.storage import LocalObjectStorage
from app.providers.tracing import InMemoryTraceRecorder
from app.providers.vision import ArkImageQualityScoringProvider, ArkPhotoProfileProvider
from app.services.task_service import TaskService, create_task_service


class AppContainer:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.tracer = InMemoryTraceRecorder()
        self.storage = LocalObjectStorage(self.settings)
        self.auth_store = AuthStore(
            self.settings.auth_store_path,
            session_max_age_days=self.settings.auth_session_max_age_days,
        )
        self.google_id_token_verifier = GoogleOAuthIdTokenVerifier(self.settings.google_client_id)
        self.photo_provider = self._create_photo_provider()
        self.search_provider = self._create_search_provider()
        self.image_provider = self._create_image_provider()
        self.image_quality_provider = self._create_image_quality_provider()
        self.wardrobe_repository = InMemoryWardrobeRepository()
        self.profile_repository = ProfileRepository()
        self.favorite_repository = FavoriteRepository()
        self.inspiration_repository = InspirationRepository()
        self.graph = StyleAgentGraph(
            settings=self.settings,
            tracer=self.tracer,
            search_provider=self.search_provider,
            image_provider=self.image_provider,
            photo_provider=self.photo_provider,
            image_quality_provider=self.image_quality_provider,
            wardrobe_products=self.wardrobe_repository.products_for_ids,
        )
        self.task_service: TaskService = create_task_service(
            self.graph,
            self.tracer,
            wardrobe_repository=self.wardrobe_repository,
        )

    def _create_photo_provider(self):
        if self.settings.model_provider == "ark" and self.settings.ark_api_key:
            return ArkPhotoProfileProvider(self.settings)
        return None

    def _create_search_provider(self):
        if self.settings.search_provider == "browser":
            return BrowserProductSearchProvider(self.settings)
        return LocalDemoSearchProvider()

    def _create_image_provider(self):
        if self.settings.image_provider == "ark" and self.settings.ark_api_key:
            return ArkSeedreamImageProvider(self.settings)
        return LocalTryOnImageProvider()

    def _create_image_quality_provider(self):
        if self.settings.model_provider == "ark" and self.settings.ark_api_key:
            return ArkImageQualityScoringProvider(self.settings)
        return None


@lru_cache
def get_container() -> AppContainer:
    return AppContainer()
