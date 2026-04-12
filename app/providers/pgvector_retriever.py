from __future__ import annotations

from typing import Any

from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.db.session import DatabaseSessionManager
from app.providers.interfaces import EmbeddingProvider, RetrievedContext, RetrieverBackend
from app.providers.retrieval_cache import (
    NoOpRetrievalCache,
    RetrievalCacheBackend,
    build_retrieval_cache_key,
)


class PgvectorBackendUnavailable(RuntimeError):
    """Raised when the configured pgvector backend cannot be used safely."""


class PgvectorRetrieverBackend(RetrieverBackend):
    def __init__(
        self,
        db_manager: DatabaseSessionManager,
        embedding_provider: EmbeddingProvider,
        *,
        settings: Settings,
        cache_backend: RetrievalCacheBackend | None = None,
        cache_ttl_seconds: int = 120,
    ) -> None:
        self.db_manager = db_manager
        self.embedding_provider = embedding_provider
        self.settings = settings
        self.cache_backend = cache_backend or NoOpRetrievalCache()
        self.cache_ttl_seconds = cache_ttl_seconds

    def search(
        self,
        query: str,
        *,
        subject: str | None = None,
        topic: str | None = None,
        task_id: str | None = None,
        top_k: int = 3,
    ) -> list[RetrievedContext]:
        cache_key = build_retrieval_cache_key(
            "pgvector",
            query,
            subject=subject,
            topic=topic,
            task_id=task_id,
            top_k=top_k,
        )
        cached = self.cache_backend.get_many(cache_key)
        if cached is not None:
            return cached

        query_embedding = self.embedding_provider.embed([query])[0]

        with self.db_manager.session_scope() as db:
            self._ensure_ready(db)
            vector_literal = self._to_vector_literal(query_embedding)
            rows = db.execute(
                text(
                    """
                    SELECT
                        chunk_id,
                        content,
                        metadata_json,
                        1 - (embedding_vector <=> CAST(:query_embedding AS vector)) AS score
                    FROM knowledge_chunks
                    WHERE embedding_vector IS NOT NULL
                      AND (:subject IS NULL OR subject = :subject)
                      AND (:topic IS NULL OR topic = :topic)
                      AND (:task_id IS NULL OR task_id = :task_id)
                    ORDER BY embedding_vector <=> CAST(:query_embedding AS vector)
                    LIMIT :top_k
                    """
                ),
                {
                    "query_embedding": vector_literal,
                    "subject": subject,
                    "topic": topic,
                    "task_id": task_id,
                    "top_k": top_k,
                },
            ).all()

        results = [
            RetrievedContext(
                chunk_id=str(row.chunk_id),
                content=str(row.content),
                score=max(float(row.score or 0.0), 0.0),
                metadata=self._coerce_metadata(row.metadata_json),
            )
            for row in rows
        ]
        self.cache_backend.set_many(
            cache_key,
            results,
            ttl_seconds=self.cache_ttl_seconds,
        )
        return results

    def is_ready(self) -> tuple[bool, str | None]:
        try:
            with self.db_manager.session_scope() as db:
                self._ensure_ready(db)
        except PgvectorBackendUnavailable as exc:
            return False, str(exc)
        return True, None

    def _ensure_ready(self, db: Session) -> None:
        bind = db.get_bind()
        if bind is None:
            raise PgvectorBackendUnavailable("Database engine is not available for pgvector.")

        if bind.dialect.name != "postgresql":
            raise PgvectorBackendUnavailable(
                "pgvector backend requires PostgreSQL; current dialect is "
                f"{bind.dialect.name!r}."
            )

        if not self._has_vector_extension(db):
            raise PgvectorBackendUnavailable(
                "PostgreSQL extension 'vector' is not installed. "
                "Run Alembic head migration on a database with pgvector enabled."
            )

        if not self._has_embedding_vector_column(db):
            raise PgvectorBackendUnavailable(
                "knowledge_chunks.embedding_vector is missing. "
                "Run the pgvector scaffold migration."
            )

    @staticmethod
    def _has_vector_extension(db: Session) -> bool:
        result = db.execute(
            text("SELECT 1 FROM pg_extension WHERE extname = 'vector' LIMIT 1")
        ).scalar_one_or_none()
        return result is not None

    @staticmethod
    def _has_embedding_vector_column(db: Session) -> bool:
        bind = db.get_bind()
        columns = inspect(bind).get_columns("knowledge_chunks")
        return any(column["name"] == "embedding_vector" for column in columns)

    @staticmethod
    def _to_vector_literal(embedding: list[float]) -> str:
        return "[" + ",".join(f"{value:.6f}" for value in embedding) + "]"

    @staticmethod
    def _coerce_metadata(raw_metadata: Any) -> dict[str, str]:
        if not isinstance(raw_metadata, dict):
            return {}
        return {str(key): str(value) for key, value in raw_metadata.items()}
