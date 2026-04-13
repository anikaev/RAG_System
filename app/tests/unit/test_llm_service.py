from __future__ import annotations

from app.providers.interfaces import LLMGenerationRequest, LLMGenerationResult, LLMProvider
from app.services.llm_service import LLMService


class FailingProvider(LLMProvider):
    def generate(self, request: LLMGenerationRequest) -> LLMGenerationResult:
        raise RuntimeError("provider unavailable")


class PathLeakingProvider(LLMProvider):
    def generate(self, request: LLMGenerationRequest) -> LLMGenerationResult:
        return LLMGenerationResult(
            response_text="Смотри файл /tmp/private/code.py и повтори это.",
            guiding_question="Что в /srv/app/main.py кажется подозрительным?",
            confidence=0.9,
            metadata={"provider": "path-leak"},
        )


class SolutionLeakingProvider(LLMProvider):
    def generate(self, request: LLMGenerationRequest) -> LLMGenerationResult:
        return LLMGenerationResult(
            response_text="```python\nprint('full solution')\n```",
            guiding_question="Готово?",
            confidence=0.8,
            metadata={"provider": "solution-leak"},
        )


class ConceptExampleProvider(LLMProvider):
    def generate(self, request: LLMGenerationRequest) -> LLMGenerationResult:
        return LLMGenerationResult(
            response_text=(
                "Цикл for повторяет действие фиксированное число раз.\n"
                "```python\nfor i in range(3):\n    print(i)\n```"
            ),
            guiding_question="Что напечатает этот пример?",
            confidence=0.78,
            metadata={"provider": "concept-example"},
        )


def test_llm_service_falls_back_to_template_when_provider_fails():
    service = LLMService(primary_provider=FailingProvider())

    result = service.generate(
        LLMGenerationRequest(
            user_message="Помоги с задачей",
            mode="hint_only",
            hint_level=1,
            response_template="Подсказка: {hint}",
            guiding_question_hint="Какой первый шаг?",
            confidence_hint=0.6,
        )
    )

    assert result.response_text.startswith("Подсказка:")
    assert result.guiding_question == "Какой первый шаг?"
    assert result.metadata["fallback_used"] is True
    assert result.metadata["fallback_reason"] == "primary_provider_failed"
    assert result.metadata["primary_provider"] == "FailingProvider"


def test_llm_service_redacts_internal_paths():
    service = LLMService(primary_provider=PathLeakingProvider())

    result = service.generate(
        LLMGenerationRequest(
            user_message="Что не так?",
            mode="code_feedback",
            hint_level=2,
        )
    )

    assert "[redacted-path]" in result.response_text
    assert result.guiding_question is not None
    assert "[redacted-path]" in result.guiding_question
    assert result.metadata["fallback_used"] is False


def test_llm_service_cuts_off_solution_leak_for_refusal_mode():
    service = LLMService(primary_provider=SolutionLeakingProvider())

    result = service.generate(
        LLMGenerationRequest(
            user_message="Дай готовый код",
            mode="refuse_full_solution",
            hint_level=1,
            refusal=True,
            response_template=(
                "Я не выдаю готовое решение целиком. {refusal_reason} "
                "Могу помочь по шагам."
            ),
            response_template_variables={"refusal_reason": "Это не поможет тебе в обучении."},
            guiding_question_hint="Какой шаг у тебя уже есть?",
            confidence_hint=0.96,
        )
    )

    assert "```" not in result.response_text
    assert "не выдаю готовое решение" in result.response_text.lower()
    assert result.metadata["fallback_used"] is True
    assert result.metadata["fallback_reason"] == "refusal_contains_code"


def test_llm_service_allows_short_example_code_for_concept_explainer():
    service = LLMService(primary_provider=ConceptExampleProvider())

    result = service.generate(
        LLMGenerationRequest(
            user_message="Объясни цикл for",
            mode="concept_explainer",
            hint_level=0,
        )
    )

    assert result.metadata["fallback_used"] is False
    assert result.metadata["fallback_reason"] is None
    assert result.metadata["provider"] == "concept-example"
    assert "```python" in result.response_text
