from __future__ import annotations

from app.core.security import sanitize_excerpt
from app.providers.interfaces import LLMGenerationRequest, LLMGenerationResult, LLMProvider


class MockLLMProvider(LLMProvider):
    def generate(self, request: LLMGenerationRequest) -> LLMGenerationResult:
        excerpt = self._build_excerpt(request)

        if request.response_template:
            return self._from_template(request, excerpt)

        return self._legacy_generate(request, excerpt)

    def _from_template(
        self, request: LLMGenerationRequest, excerpt: str,
    ) -> LLMGenerationResult:
        template = request.response_template
        if template is None:
            return self._legacy_generate(request, excerpt)

        fill = {
            "hint": excerpt,
            "reason": "не хватает условия задачи или текущего шага",
            "requested_context": "условие задачи, номер задания или свой текущий код",
            "concept_summary": excerpt,
            "code_feedback": excerpt,
            "refusal_reason": "Это не поможет тебе в обучении.",
        }
        fill.update(request.response_template_variables)
        response_text = template.format_map(_SafeFormatMap(fill))

        confidence = request.confidence_hint if request.confidence_hint is not None else self._pick_confidence(request)

        return LLMGenerationResult(
            response_text=response_text,
            guiding_question=request.guiding_question_hint,
            confidence=confidence,
            metadata={
                "provider": "mock",
                "mode": request.mode,
                "template_used": True,
                "pedagogical_instruction": request.pedagogical_instruction,
            },
        )

    def _legacy_generate(
        self, request: LLMGenerationRequest, excerpt: str,
    ) -> LLMGenerationResult:
        if request.mode == "refuse_full_solution":
            return LLMGenerationResult(
                response_text=(
                    "Я не выдаю готовое решение целиком. Вместо этого помогу по шагам: "
                    f"{excerpt}"
                ),
                guiding_question=(
                    request.guiding_question_hint
                    or "Какой промежуточный шаг у тебя уже получился?"
                ),
                confidence=self._resolve_confidence(request, 0.96),
                metadata={
                    "provider": "mock",
                    "mode": request.mode,
                    "pedagogical_instruction": request.pedagogical_instruction,
                },
            )

        if request.mode == "clarify":
            return LLMGenerationResult(
                response_text=(
                    "Нужно чуть больше контекста, чтобы подсказка была точной. "
                    f"{excerpt}"
                ),
                guiding_question=(
                    request.guiding_question_hint
                    or "Пришли условие задачи, номер задания или свой текущий код."
                ),
                confidence=self._resolve_confidence(request, 0.42),
                metadata={
                    "provider": "mock",
                    "mode": request.mode,
                    "pedagogical_instruction": request.pedagogical_instruction,
                },
            )

        if request.mode == "concept_explainer":
            return LLMGenerationResult(
                response_text=(
                    f"Ключевая идея: {excerpt} Сначала сформулируй правило своими словами, "
                    "потом проверь его на небольшом примере."
                ),
                guiding_question=(
                    request.guiding_question_hint
                    or "Какой небольшой пример по этой теме ты можешь разобрать сам?"
                ),
                confidence=self._resolve_confidence(
                    request,
                    0.84 if request.context else 0.58,
                ),
                metadata={
                    "provider": "mock",
                    "mode": request.mode,
                    "pedagogical_instruction": request.pedagogical_instruction,
                },
            )

        if request.mode == "code_feedback":
            return LLMGenerationResult(
                response_text=(
                    f"Смотри на код как на последовательность состояний. {excerpt} "
                    "Сначала проверь инвариант и крайние случаи."
                ),
                guiding_question=(
                    request.guiding_question_hint
                    or "На каком входе программа начинает вести себя не так, как ожидается?"
                ),
                confidence=self._resolve_confidence(request, 0.73),
                metadata={
                    "provider": "mock",
                    "mode": request.mode,
                    "pedagogical_instruction": request.pedagogical_instruction,
                },
            )

        return LLMGenerationResult(
            response_text=(
                f"Подсказка уровня {request.hint_level}: {excerpt} "
                "Определи, какое состояние алгоритма должно быть известно после следующего шага."
            ),
            guiding_question=(
                request.guiding_question_hint
                or "Какое промежуточное значение или условие нужно вычислить первым?"
            ),
            confidence=self._resolve_confidence(
                request,
                0.82 if request.context else 0.55,
            ),
            metadata={
                "provider": "mock",
                "mode": request.mode,
                "pedagogical_instruction": request.pedagogical_instruction,
            },
        )

    def _pick_confidence(self, request: LLMGenerationRequest) -> float:
        if request.mode == "refuse_full_solution":
            return 0.96
        if request.mode == "clarify":
            return 0.42
        if request.mode in ("concept_explainer", "hint_only"):
            return 0.84 if request.context else 0.58
        if request.mode == "code_feedback":
            return 0.73
        return 0.55

    @staticmethod
    def _resolve_confidence(request: LLMGenerationRequest, default: float) -> float:
        if request.confidence_hint is not None:
            return request.confidence_hint
        return default

    @staticmethod
    def _build_excerpt(request: LLMGenerationRequest) -> str:
        if not request.context:
            return (
                "Начни с формализации входных данных, ожидаемого результата и одной проверки "
                "на минимальном примере."
            )
        return sanitize_excerpt(request.context[0].content)


class _SafeFormatMap(dict):
    """Returns the key wrapped in braces for any missing placeholder."""

    def __missing__(self, key: str) -> str:
        return f"{{{key}}}"
