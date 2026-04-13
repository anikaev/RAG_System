from __future__ import annotations

import logging

from app.core.config import Settings
from app.db.session import DatabaseSessionManager
from app.providers.compatible_api_llm_provider import CompatibleAPILLMProvider
from app.providers.database_retriever import DatabaseLexicalRetriever
from app.providers.docker_code_runner import DockerCodeExecutionBackend
from app.providers.fallback_retriever import FallbackRetriever
from app.providers.interfaces import CodeExecutionBackend, EmbeddingProvider, LLMProvider, RetrieverBackend
from app.providers.jina_embedding_provider import JinaEmbeddingProvider
from app.providers.mock_embedding_provider import MockEmbeddingProvider
from app.providers.mock_llm_provider import MockLLMProvider
from app.providers.pgvector_retriever import PgvectorRetrieverBackend
from app.providers.retrieval_cache import (
    NoOpRetrievalCache,
    RedisRetrievalCache,
    RetrievalCacheBackend,
)
from app.providers.stub_code_runner import LocalStubCodeRunner

logger = logging.getLogger(__name__)


def build_llm_provider(settings: Settings) -> LLMProvider:
    if settings.llm_provider_mode == "mock":
        return MockLLMProvider()
    if settings.llm_provider_mode == "compatible_api":
        return CompatibleAPILLMProvider(settings)
    raise ValueError(f"Unsupported llm_provider_mode: {settings.llm_provider_mode}")


def build_embedding_provider(settings: Settings) -> EmbeddingProvider:
    if settings.embedding_provider_mode == "mock":
        return MockEmbeddingProvider(dimensions=settings.pgvector_dimensions)
    if settings.embedding_provider_mode == "jina":
        return JinaEmbeddingProvider(settings)
    raise ValueError(
        f"Unsupported embedding_provider_mode: {settings.embedding_provider_mode}"
    )


def build_retriever_backend(
    settings: Settings,
    *,
    embedding_provider: EmbeddingProvider,
    db_manager: DatabaseSessionManager | None = None,
) -> RetrieverBackend:
    cache_backend = build_retrieval_cache_backend(settings)
    fallback_backend = FallbackRetriever(
        settings.kb_seed_path,
        chunk_size_chars=settings.kb_chunk_size_chars,
        overlap_paragraphs=settings.kb_chunk_overlap_paragraphs,
        cache_backend=cache_backend,
        cache_ttl_seconds=settings.retrieval_cache_ttl_seconds,
    )
    database_backend = (
        DatabaseLexicalRetriever(
            db_manager,
            cache_backend=cache_backend,
            cache_ttl_seconds=settings.retrieval_cache_ttl_seconds,
        )
        if db_manager is not None
        else None
    )
    if settings.retriever_backend_mode == "fallback":
        if database_backend is not None and database_backend.is_ready():
            return database_backend
        return fallback_backend

    if settings.retriever_backend_mode == "pgvector":
        if db_manager is None:
            if settings.retriever_fallback_to_lexical:
                return fallback_backend
            raise ValueError(
                "pgvector retriever requires a live database connection, but db_manager is not available."
            )

        pgvector_backend = PgvectorRetrieverBackend(
            db_manager=db_manager,
            embedding_provider=embedding_provider,
            settings=settings,
            cache_backend=cache_backend,
            cache_ttl_seconds=settings.retrieval_cache_ttl_seconds,
        )
        ready, _reason = pgvector_backend.is_ready()
        if ready:
            return pgvector_backend
        if settings.retriever_fallback_to_lexical:
            if database_backend is not None and database_backend.is_ready():
                return database_backend
            return fallback_backend
        raise ValueError(
            "pgvector retriever is configured, but the backend is not ready. "
            "Apply the pgvector migration or enable lexical fallback."
        )

    raise ValueError(f"Unsupported retriever_backend_mode: {settings.retriever_backend_mode}")


def build_code_execution_backend(settings: Settings) -> CodeExecutionBackend:
    if settings.code_execution_backend_mode == "stub":
        return LocalStubCodeRunner()
    if settings.code_execution_backend_mode == "docker":
        return DockerCodeExecutionBackend(settings)
    raise ValueError(
        "Unsupported code_execution_backend_mode: "
        f"{settings.code_execution_backend_mode}"
    )


def build_retrieval_cache_backend(settings: Settings) -> RetrievalCacheBackend:
    if settings.retrieval_cache_backend_mode == "disabled":
        return NoOpRetrievalCache()

    redis_cache = RedisRetrievalCache(settings.redis_url)
    if redis_cache.is_available():
        return redis_cache

    logger.warning(
        "redis.cache_unavailable_falling_back_to_noop redis_url=%s mode=%s",
        settings.redis_url,
        settings.retrieval_cache_backend_mode,
    )
    return NoOpRetrievalCache()
