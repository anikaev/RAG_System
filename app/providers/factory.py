from __future__ import annotations

from app.core.config import Settings
from app.providers.fallback_retriever import FallbackRetriever
from app.providers.interfaces import CodeExecutionBackend, EmbeddingProvider, LLMProvider, RetrieverBackend
from app.providers.mock_embedding_provider import MockEmbeddingProvider
from app.providers.mock_llm_provider import MockLLMProvider
from app.providers.stub_code_runner import LocalStubCodeRunner


def build_llm_provider(settings: Settings) -> LLMProvider:
    if settings.llm_provider_mode == "mock":
        return MockLLMProvider()
    raise ValueError(f"Unsupported llm_provider_mode: {settings.llm_provider_mode}")


def build_embedding_provider(settings: Settings) -> EmbeddingProvider:
    if settings.embedding_provider_mode == "mock":
        return MockEmbeddingProvider()
    raise ValueError(
        f"Unsupported embedding_provider_mode: {settings.embedding_provider_mode}"
    )


def build_retriever_backend(settings: Settings) -> RetrieverBackend:
    if settings.retriever_backend_mode == "fallback":
        return FallbackRetriever(
            settings.kb_seed_path,
            chunk_size_chars=settings.kb_chunk_size_chars,
            overlap_paragraphs=settings.kb_chunk_overlap_paragraphs,
        )
    raise ValueError(
        f"Unsupported retriever_backend_mode: {settings.retriever_backend_mode}"
    )


def build_code_execution_backend(settings: Settings) -> CodeExecutionBackend:
    if settings.code_execution_backend_mode == "stub":
        return LocalStubCodeRunner()
    raise ValueError(
        "Unsupported code_execution_backend_mode: "
        f"{settings.code_execution_backend_mode}"
    )
