from __future__ import annotations

from app.providers import (
    LLMGenerationRequest,
    MockEmbeddingProvider,
    MockLLMProvider,
)
from app.providers.interfaces import RetrievedContext


def test_mock_embedding_provider_is_deterministic():
    provider = MockEmbeddingProvider()

    first = provider.embed(["цикл for в python"])[0]
    second = provider.embed(["цикл for в python"])[0]
    third = provider.embed(["массивы и префиксные суммы"])[0]

    assert first == second
    assert first != third
    assert len(first) == 8


def test_mock_llm_provider_returns_structured_response():
    provider = MockLLMProvider()

    response = provider.generate(
        LLMGenerationRequest(
            user_message="Объясни цикл for",
            mode="concept_explainer",
            hint_level=0,
            context=[
                RetrievedContext(
                    chunk_id="loops:0",
                    content="Цикл for удобен, когда количество шагов заранее известно.",
                    score=1.0,
                    metadata={"topic": "python_loops"},
                )
            ],
        )
    )

    assert response.response_text
    assert response.guiding_question
    assert 0.0 <= response.confidence <= 1.0
    assert response.metadata["provider"] == "mock"


def test_mock_llm_provider_renders_response_template():
    provider = MockLLMProvider()

    response = provider.generate(
        LLMGenerationRequest(
            user_message="Помоги с задачей",
            mode="hint_only",
            hint_level=1,
            response_template="Шаблонная подсказка: {hint}",
            response_template_variables={"hint": "сначала выдели инвариант"},
            guiding_question_hint="С чего ты начнешь проверку?",
            confidence_hint=0.61,
            pedagogical_instruction="Дай мягкую подсказку без готового решения.",
            context=[
                RetrievedContext(
                    chunk_id="arrays:0",
                    content="Сначала выдели ключевое состояние алгоритма и проверь его на примере.",
                    score=1.0,
                    metadata={"topic": "task_27"},
                )
            ],
        )
    )

    assert response.response_text.startswith("Шаблонная подсказка:")
    assert "сначала выдели инвариант" in response.response_text.lower()
    assert response.guiding_question == "С чего ты начнешь проверку?"
    assert response.confidence == 0.61
    assert response.metadata["template_used"] is True
    assert response.metadata["pedagogical_instruction"] == (
        "Дай мягкую подсказку без готового решения."
    )
