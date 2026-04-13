from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.core.config import Settings
from app.providers.interfaces import RetrieverBackend
from app.services.container import ServiceContainer


@dataclass(slots=True)
class RetrieverDiagnostics:
    backend: str
    ready: bool | None
    status: str | None


def build_runtime_summary(
    *,
    settings: Settings,
    services: ServiceContainer,
) -> dict[str, str | bool | None]:
    retriever = describe_retriever(services.retriever)
    return {
        "session_backend": _component_name(services.session_store),
        "retriever_backend": retriever.backend,
        "retriever_ready": retriever.ready,
        "retriever_status": retriever.status,
        "embedding_provider": _component_name(services.embedding_provider),
        "llm_provider": _component_name(services.llm_provider),
        "code_execution_backend": _component_name(services.code_execution_backend),
        "configured_session_backend": settings.session_backend,
        "configured_retriever_backend": settings.retriever_backend_mode,
        "configured_embedding_provider": settings.embedding_provider_mode,
    }


def describe_retriever(retriever: RetrieverBackend) -> RetrieverDiagnostics:
    ready: bool | None = None
    status: str | None = None
    readiness_probe = getattr(retriever, "is_ready", None)
    if callable(readiness_probe):
        result = readiness_probe()
        if isinstance(result, tuple) and len(result) == 2 and isinstance(result[0], bool):
            ready = result[0]
            status = str(result[1]) if result[1] is not None else None
        elif isinstance(result, bool):
            ready = result
    return RetrieverDiagnostics(
        backend=_component_name(retriever),
        ready=ready,
        status=status,
    )


def _component_name(component: Any) -> str:
    mapping = {
        "InMemorySessionStore": "memory",
        "DatabaseSessionStore": "database",
        "FallbackRetriever": "fallback",
        "DatabaseLexicalRetriever": "database_lexical",
        "PgvectorRetrieverBackend": "pgvector",
        "MockEmbeddingProvider": "mock",
        "JinaEmbeddingProvider": "jina",
        "MockLLMProvider": "mock",
        "CompatibleAPILLMProvider": "compatible_api",
        "LocalStubCodeRunner": "stub",
        "DockerCodeExecutionBackend": "docker",
    }
    return mapping.get(type(component).__name__, type(component).__name__)
