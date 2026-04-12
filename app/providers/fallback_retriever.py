from __future__ import annotations

from pathlib import Path

from app.kb.ingest import build_seed_chunks
from app.providers.interfaces import RetrievedContext, RetrieverBackend
from app.providers.lexical_retrieval import rank_retrieved_contexts
from app.providers.retrieval_cache import (
    NoOpRetrievalCache,
    RetrievalCacheBackend,
    build_retrieval_cache_key,
)


class FallbackRetriever(RetrieverBackend):
    def __init__(
        self,
        seed_path: Path,
        *,
        chunk_size_chars: int = 320,
        overlap_paragraphs: int = 1,
        cache_backend: RetrievalCacheBackend | None = None,
        cache_ttl_seconds: int = 120,
    ) -> None:
        self.seed_path = seed_path
        self.chunk_size_chars = chunk_size_chars
        self.overlap_paragraphs = overlap_paragraphs
        self.cache_backend = cache_backend or NoOpRetrievalCache()
        self.cache_ttl_seconds = cache_ttl_seconds
        self._chunks = self._load_chunks()

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
            "fallback",
            query,
            subject=subject,
            topic=topic,
            task_id=task_id,
            top_k=top_k,
        )
        cached = self.cache_backend.get_many(cache_key)
        if cached is not None:
            return cached

        results = rank_retrieved_contexts(
            query,
            self._chunks,
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

    def _load_chunks(self) -> list[RetrievedContext]:
        return [
            RetrievedContext(
                chunk_id=chunk.chunk_id,
                content=chunk.content,
                score=0.0,
                metadata=chunk.metadata_json,
            )
            for chunk in build_seed_chunks(
                self.seed_path,
                target_size_chars=self.chunk_size_chars,
                overlap_paragraphs=self.overlap_paragraphs,
            )
        ]
