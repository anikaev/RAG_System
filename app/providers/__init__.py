"""Provider abstractions and mock/fallback implementations."""

from app.providers.compatible_api_llm_provider import CompatibleAPILLMProvider
from app.providers.database_retriever import DatabaseLexicalRetriever
from app.providers.docker_code_runner import DockerCodeExecutionBackend
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
from app.providers.pgvector_retriever import PgvectorBackendUnavailable, PgvectorRetrieverBackend

__all__ = [
    "CompatibleAPILLMProvider",
    "CodeExecutionBackend",
    "DockerCodeExecutionBackend",
    "DatabaseLexicalRetriever",
    "CodeExecutionRequest",
    "CodeExecutionResult",
    "EmbeddingProvider",
    "LLMGenerationRequest",
    "LLMGenerationResult",
    "LLMProvider",
    "MockEmbeddingProvider",
    "MockLLMProvider",
    "PgvectorBackendUnavailable",
    "PgvectorRetrieverBackend",
    "RetrievedContext",
    "RetrieverBackend",
    "build_code_execution_backend",
    "build_embedding_provider",
    "build_llm_provider",
    "build_retriever_backend",
]
