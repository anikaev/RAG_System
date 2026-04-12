from __future__ import annotations

import pytest

from app.core.config import Settings
from app.providers.fallback_retriever import FallbackRetriever
from app.providers.mock_embedding_provider import MockEmbeddingProvider
from app.providers.mock_llm_provider import MockLLMProvider
from app.providers.openai_llm_provider import OpenAILLMProvider
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


def test_service_container_supports_openai_provider_mode():
    settings = Settings(
        session_backend="memory",
        llm_provider_mode="openai",
        seed_demo_data_on_startup=False,
    )

    container = build_service_container(settings)

    assert isinstance(container.llm_provider, OpenAILLMProvider)


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
