from __future__ import annotations

from app.providers.persistence import InMemoryTaskRepository, TaskRepository


class PostgresTaskRepository(InMemoryTaskRepository):
    """PostgreSQL/pgvector repository placeholder.

    The first implementation keeps the TaskRepository contract identical to the in-memory
    repository so the API and graph are not coupled to storage. Production migration should
    replace the inherited methods with SQL operations and vector indexes for wardrobe/product
    retrieval.
    """

    def __init__(self, dsn: str) -> None:
        try:
            import psycopg  # noqa: F401
            import pgvector  # noqa: F401
        except Exception as exc:  # pragma: no cover - optional production dependency
            raise RuntimeError("psycopg and pgvector are required for PostgresTaskRepository") from exc
        super().__init__()
        self.dsn = dsn


def create_postgres_repository(dsn: str | None) -> TaskRepository | None:
    if not dsn:
        return None
    return PostgresTaskRepository(dsn)

