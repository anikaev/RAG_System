from __future__ import annotations

from typing import Any

from app.db.repositories import KnowledgeChunkRepository
from app.db.session import DatabaseSessionManager
from app.providers.interfaces import RetrievedContext, RetrieverBackend
from app.providers.lexical_retrieval import rank_retrieved_contexts
from app.providers.retrieval_cache import (
    NoOpRetrievalCache,
    RetrievalCacheBackend,
    build_retrieval_cache_key,
)


class DatabaseLexicalRetriever(RetrieverBackend):
    def __init__(
        self,
        db_manager: DatabaseSessionManager,
        *,
        cache_backend: RetrievalCacheBackend | None = None,
        cache_ttl_seconds: int = 120,
    ) -> None:
        self.db_manager = db_manager
        self.repository = KnowledgeChunkRepository()
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
            "database_lexical",
            query,
            subject=subject,
            topic=topic,
            task_id=task_id,
            top_k=top_k,
        )
        cached = self.cache_backend.get_many(cache_key)
        if cached is not None:
            return cached

        with self.db_manager.session_scope() as db:
            rows = self.repository.list_for_retrieval(
                db,
                subject=subject,
                topic=topic,
                task_id=task_id,
            )
        chunks = [
            RetrievedContext(
                chunk_id=row.chunk_id,
                content=row.content,
                score=0.0,
                metadata=self._coerce_metadata(
                    row.metadata_json,
                    subject=row.subject,
                    topic=row.topic,
                    task_id=row.task_id,
                    source_id=row.source_id,
                ),
            )
            for row in rows
        ]
        results = rank_retrieved_contexts(
            query,
            chunks,
            subject=subject,
            topic=topic,
            task_id=task_id,
            top_k=top_k,
        )
        self.cache_backend.set_many(
            cache_key,
            results,
            ttl_seconds=self.cache_ttl_seconds,
        )
        return results

    def is_ready(self) -> bool:
        try:
            with self.db_manager.session_scope() as db:
                return self.repository.count(db) > 0
        except Exception:
            return False

    @staticmethod
    def _coerce_metadata(
        raw_metadata: Any,
        *,
        subject: str,
        topic: str | None,
        task_id: str | None,
        source_id: str,
    ) -> dict[str, str]:
        metadata: dict[str, str] = {}
        if isinstance(raw_metadata, dict):
            metadata.update({str(key): str(value) for key, value in raw_metadata.items()})
        metadata.setdefault("subject", subject)
        if topic is not None:
            metadata.setdefault("topic", topic)
        if task_id is not None:
            metadata.setdefault("task_id", task_id)
        metadata.setdefault("source_id", source_id)
        return metadata
