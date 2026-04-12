from __future__ import annotations

from app.core.config import Settings
from app.db.session import DatabaseSessionManager
from app.providers.compatible_api_llm_provider import CompatibleAPILLMProvider
from app.providers.docker_code_runner import DockerCodeExecutionBackend
from app.providers.fallback_retriever import FallbackRetriever
from app.providers.interfaces import CodeExecutionBackend, EmbeddingProvider, LLMProvider, RetrieverBackend
from app.providers.mock_embedding_provider import MockEmbeddingProvider
from app.providers.mock_llm_provider import MockLLMProvider
from app.providers.pgvector_retriever import PgvectorRetrieverBackend
from app.providers.stub_code_runner import LocalStubCodeRunner


def build_llm_provider(settings: Settings) -> LLMProvider:
    if settings.llm_provider_mode == "mock":
        return MockLLMProvider()
    if settings.llm_provider_mode == "compatible_api":
        return CompatibleAPILLMProvider(settings)
    raise ValueError(f"Unsupported llm_provider_mode: {settings.llm_provider_mode}")


def build_embedding_provider(settings: Settings) -> EmbeddingProvider:
    if settings.embedding_provider_mode == "mock":
        return MockEmbeddingProvider()
    raise ValueError(
        f"Unsupported embedding_provider_mode: {settings.embedding_provider_mode}"
    )


def build_retriever_backend(
    settings: Settings,
    *,
    embedding_provider: EmbeddingProvider,
    db_manager: DatabaseSessionManager | None = None,
) -> RetrieverBackend:
    fallback_backend = FallbackRetriever(
        settings.kb_seed_path,
        chunk_size_chars=settings.kb_chunk_size_chars,
        overlap_paragraphs=settings.kb_chunk_overlap_paragraphs,
    )
    if settings.retriever_backend_mode == "fallback":
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
        )
        ready, _reason = pgvector_backend.is_ready()
        if ready:
            return pgvector_backend
        if settings.retriever_fallback_to_lexical:
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
