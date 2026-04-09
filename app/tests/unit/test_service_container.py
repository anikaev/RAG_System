from __future__ import annotations

from app.core.config import Settings
from app.providers.mock_embedding_provider import MockEmbeddingProvider
from app.providers.mock_llm_provider import MockLLMProvider
from app.providers.stub_code_runner import LocalStubCodeRunner
from app.services.container import build_service_container


def test_service_container_wires_mock_components():
    settings = Settings(
        session_backend="memory",
        seed_demo_data_on_startup=False,
    )

    container = build_service_container(settings)

    assert isinstance(container.llm_provider, MockLLMProvider)
    assert isinstance(container.embedding_provider, MockEmbeddingProvider)
    assert isinstance(container.code_execution_backend, LocalStubCodeRunner)
