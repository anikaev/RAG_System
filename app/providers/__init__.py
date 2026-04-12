"""Provider abstractions and mock/fallback implementations."""

from app.providers.factory import (
    build_code_execution_backend,
    build_embedding_provider,
    build_llm_provider,
    build_retriever_backend,
)
from app.providers.interfaces import (
    CodeExecutionBackend,
    CodeExecutionRequest,
    CodeExecutionResult,
    EmbeddingProvider,
    LLMGenerationRequest,
    LLMGenerationResult,
    LLMProvider,
    RetrievedContext,
    RetrieverBackend,
)
from app.providers.mock_embedding_provider import MockEmbeddingProvider
from app.providers.mock_llm_provider import MockLLMProvider
from app.providers.openai_llm_provider import OpenAILLMProvider
from app.providers.pgvector_retriever import PgvectorBackendUnavailable, PgvectorRetrieverBackend

__all__ = [
    "CodeExecutionBackend",
    "CodeExecutionRequest",
    "CodeExecutionResult",
    "EmbeddingProvider",
    "LLMGenerationRequest",
    "LLMGenerationResult",
    "LLMProvider",
    "MockEmbeddingProvider",
    "MockLLMProvider",
    "OpenAILLMProvider",
    "PgvectorBackendUnavailable",
    "PgvectorRetrieverBackend",
    "RetrievedContext",
    "RetrieverBackend",
    "build_code_execution_backend",
    "build_embedding_provider",
    "build_llm_provider",
    "build_retriever_backend",
]
