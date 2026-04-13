from __future__ import annotations

import pytest

from app.core.config import Settings
from app.providers.compatible_api_llm_provider import CompatibleAPILLMProvider
from app.providers.database_retriever import DatabaseLexicalRetriever
from app.providers.docker_code_runner import DockerCodeExecutionBackend
from app.providers.fallback_retriever import FallbackRetriever
from app.providers.jina_embedding_provider import JinaEmbeddingProvider
from app.providers.mock_embedding_provider import MockEmbeddingProvider
from app.providers.mock_llm_provider import MockLLMProvider
from app.providers.stub_code_runner import LocalStubCodeRunner
from app.services.container import build_service_container
from app.services.llm_service import LLMService


def test_service_container_wires_mock_components():
    settings = Settings(
        session_backend="memory",
        seed_demo_data_on_startup=False,
    )

    container = build_service_container(settings)

    assert isinstance(container.llm_provider, MockLLMProvider)
    assert isinstance(container.llm_service, LLMService)
    assert isinstance(container.embedding_provider, MockEmbeddingProvider)
    assert isinstance(container.code_execution_backend, LocalStubCodeRunner)
    assert isinstance(container.retriever, FallbackRetriever)


def test_service_container_supports_compatible_api_provider_mode():
    settings = Settings(
        session_backend="memory",
        llm_provider_mode="compatible_api",
        seed_demo_data_on_startup=False,
    )

    container = build_service_container(settings)

    assert isinstance(container.llm_provider, CompatibleAPILLMProvider)


def test_service_container_supports_jina_embedding_provider_mode():
    settings = Settings(
        session_backend="memory",
        embedding_provider_mode="jina",
        embedding_api_key="jina_test_key",
        seed_demo_data_on_startup=False,
    )

    container = build_service_container(settings)

    assert isinstance(container.embedding_provider, JinaEmbeddingProvider)


def test_service_container_supports_docker_code_runner_mode():
    settings = Settings(
        session_backend="memory",
        code_execution_backend_mode="docker",
        seed_demo_data_on_startup=False,
    )

    container = build_service_container(settings)

    assert isinstance(container.code_execution_backend, DockerCodeExecutionBackend)


def test_service_container_falls_back_when_pgvector_requested_without_database():
    settings = Settings(
        session_backend="memory",
        retriever_backend_mode="pgvector",
        retriever_fallback_to_lexical=True,
        seed_demo_data_on_startup=False,
    )

    container = build_service_container(settings)

    assert isinstance(container.retriever, FallbackRetriever)


def test_service_container_raises_when_pgvector_requires_database_and_fallback_disabled():
    settings = Settings(
        session_backend="memory",
        retriever_backend_mode="pgvector",
        retriever_fallback_to_lexical=False,
        seed_demo_data_on_startup=False,
    )

    with pytest.raises(ValueError):
        build_service_container(settings)


def test_service_container_prefers_database_retriever_when_database_is_available(tmp_path):
    settings = Settings(
        postgres_url=f"sqlite+pysqlite:///{tmp_path / 'container.db'}",
        session_backend="database",
        database_bootstrap_schema=True,
        database_fallback_to_memory=False,
        seed_demo_data_on_startup=True,
    )

    container = build_service_container(settings)

    assert isinstance(container.retriever, DatabaseLexicalRetriever)
