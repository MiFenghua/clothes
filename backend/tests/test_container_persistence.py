from __future__ import annotations

import pytest

from app.config import get_settings
from app.providers.persistence import InMemoryFavoritesRepository, InMemoryTaskRepository, InMemoryWardrobeRepository
from app.providers.postgres import (
    PostgresAuthStore,
    PostgresDatabase,
    PostgresFavoritesRepository,
    PostgresTaskRepository,
    PostgresTraceRecorder,
    PostgresWardrobeRepository,
)
from app.services.container import get_container


@pytest.fixture(autouse=True)
def clear_container_caches():
    get_container.cache_clear()
    get_settings.cache_clear()
    yield
    get_container.cache_clear()
    get_settings.cache_clear()


def test_container_uses_local_persistence_without_postgres_dsn(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("STYLE_BACKEND_POSTGRES_DSN", raising=False)
    get_container.cache_clear()
    get_settings.cache_clear()

    container = get_container()

    assert isinstance(container.task_service.repository, InMemoryTaskRepository)
    assert isinstance(container.task_service.wardrobe_repository, InMemoryWardrobeRepository)
    assert isinstance(container.task_service.favorites_repository, InMemoryFavoritesRepository)


def test_container_uses_postgres_persistence_with_postgres_dsn(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    dsn = "postgresql://style:test@localhost:5432/style_test"
    checked_dsns: list[str] = []

    def fake_check_connection(self: PostgresDatabase) -> bool:
        checked_dsns.append(self.dsn)
        return True

    monkeypatch.setenv("STYLE_BACKEND_POSTGRES_DSN", dsn)
    monkeypatch.setattr(PostgresDatabase, "check_connection", fake_check_connection)
    get_container.cache_clear()
    get_settings.cache_clear()

    container = get_container()

    assert checked_dsns == [dsn]
    assert isinstance(container.auth_store, PostgresAuthStore)
    assert isinstance(container.tracer, PostgresTraceRecorder)
    assert isinstance(container.task_service.repository, PostgresTaskRepository)
    assert isinstance(container.task_service.wardrobe_repository, PostgresWardrobeRepository)
    assert isinstance(container.task_service.favorites_repository, PostgresFavoritesRepository)
