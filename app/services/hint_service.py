from __future__ import annotations

from dataclasses import dataclass

from app.core.policies import (
    has_escalation_signal,
    has_near_solution_signal,
    has_specific_error_signal,
    is_code_feedback_request,
    is_concept_question,
    should_refuse_full_solution,
    wants_stronger_hints,
)
from app.core.prompts import (
    CLARIFY_RESPONSE_TEMPLATE,
    CODE_FEEDBACK_RESPONSE_TEMPLATE,
    CONCEPT_EXPLAINER_RESPONSE_TEMPLATE,
    GUIDING_QUESTIONS,
    HINT_LEVEL_DESCRIPTIONS,
    HINT_ONLY_GUIDING_QUESTIONS,
    HINT_ONLY_RESPONSE_TEMPLATES,
    REFUSE_FULL_SOLUTION_RESPONSE_TEMPLATE,
)
from app.schemas.chat import ChatMode

MIN_HINT_LEVEL = 0
MAX_HINT_LEVEL = 4
NEAR_SOLUTION_JUMP_THRESHOLD = 2


_MODE_TEMPLATES: dict[str, str] = {
    ChatMode.CLARIFY: CLARIFY_RESPONSE_TEMPLATE,
    ChatMode.CONCEPT_EXPLAINER: CONCEPT_EXPLAINER_RESPONSE_TEMPLATE,
    ChatMode.CODE_FEEDBACK: CODE_FEEDBACK_RESPONSE_TEMPLATE,
    ChatMode.REFUSE_FULL_SOLUTION: REFUSE_FULL_SOLUTION_RESPONSE_TEMPLATE,
}


@dataclass(frozen=True, slots=True)
class HintDecision:
    mode: ChatMode
    next_hint_level: int
    refusal: bool
    guiding_question: str | None
    pedagogical_instruction: str | None
    confidence_hint: float | None
    hint_level_description: str | None
    response_template: str | None
    response_template_variables: dict[str, str]


class HintService:
    """Pedagogical hint progression engine.

    Responsible for deciding which mode to use, advancing (or holding) the
    hint level, and producing an appropriate guiding question — all without
    knowing anything about retrieval or LLM generation.
    """

    def evaluate(
        self,
        *,
        message: str,
        current_hint_level: int,
        has_context: bool,
        has_code: bool = False,
    ) -> HintDecision:
        if should_refuse_full_solution(message):
            return self._decision(
                mode=ChatMode.REFUSE_FULL_SOLUTION,
                level=current_hint_level,
                refusal=True,
                has_context=has_context,
            )

        if has_code or is_code_feedback_request(message) or has_specific_error_signal(message):
            level = self._advance_for_code_feedback(message, current_hint_level)
            return self._decision(
                mode=ChatMode.CODE_FEEDBACK,
                level=level,
                refusal=False,
                has_context=has_context,
            )

        if not has_context and len(message.split()) < 4:
            return self._decision(
                mode=ChatMode.CLARIFY,
                level=MIN_HINT_LEVEL,
                refusal=False,
                has_context=has_context,
            )

        if is_concept_question(message):
            return self._decision(
                mode=ChatMode.CONCEPT_EXPLAINER,
                level=current_hint_level,
                refusal=False,
                has_context=has_context,
            )

        next_level = self._compute_next_hint_level(message, current_hint_level)
        return self._decision(
            mode=ChatMode.HINT_ONLY,
            level=next_level,
            refusal=False,
            has_context=has_context,
        )

    def _compute_next_hint_level(self, message: str, current: int) -> int:
        if has_near_solution_signal(message):
            proposed = current + 2
        elif has_escalation_signal(message) or wants_stronger_hints(message):
            proposed = current + 1
        else:
            proposed = current + 1

        return self._clamp_level(proposed, current)

    def _advance_for_code_feedback(self, message: str, current: int) -> int:
        if has_specific_error_signal(message):
            return self._clamp_level(max(current, 3), current)
        return self._clamp_level(current + 1, current)

    @staticmethod
    def _clamp_level(proposed: int, current: int) -> int:
        """Enforce pedagogical guardrails on level transitions.

        * Never exceed MAX_HINT_LEVEL.
        * Never jump to level 4 from levels 0-1 (must pass through 2-3 first).
        * Never decrease the level.
        """
        proposed = max(proposed, current)
        if current < NEAR_SOLUTION_JUMP_THRESHOLD and proposed >= MAX_HINT_LEVEL:
            proposed = MAX_HINT_LEVEL - 1
        return min(proposed, MAX_HINT_LEVEL)

    def _decision(
        self,
        *,
        mode: ChatMode,
        level: int,
        refusal: bool,
        has_context: bool,
    ) -> HintDecision:
        return HintDecision(
            mode=mode,
            next_hint_level=level,
            refusal=refusal,
            guiding_question=self._pick_guiding_question(mode, level),
            pedagogical_instruction=self._pick_pedagogical_instruction(mode, level),
            confidence_hint=self._pick_confidence_hint(mode, has_context=has_context),
            hint_level_description=HINT_LEVEL_DESCRIPTIONS.get(level),
            response_template=self._pick_response_template(mode, level),
            response_template_variables=self._pick_response_template_variables(mode),
        )

    @staticmethod
    def _pick_guiding_question(mode: ChatMode, level: int) -> str | None:
        if mode == ChatMode.HINT_ONLY:
            return HINT_ONLY_GUIDING_QUESTIONS.get(level)
        return GUIDING_QUESTIONS.get(mode.value)

    @staticmethod
    def _pick_pedagogical_instruction(mode: ChatMode, level: int) -> str:
        if mode == ChatMode.HINT_ONLY:
            return HINT_LEVEL_DESCRIPTIONS[level]
        if mode == ChatMode.CLARIFY:
            return (
                "Не давай содержательную подсказку, пока пользователь не уточнит "
                "условие, текущий шаг или свой код."
            )
        if mode == ChatMode.CONCEPT_EXPLAINER:
            return (
                "Объясни принцип на простом примере и не переходи к полному решению "
                "конкретной задачи."
            )
        if mode == ChatMode.CODE_FEEDBACK:
            return (
                "Разбери проблему в коде и предложи следующий отладочный шаг без "
                "переписывания решения целиком."
            )
        if mode == ChatMode.REFUSE_FULL_SOLUTION:
            return (
                "Откажи в выдаче полного решения и перенаправь пользователя к пошаговой помощи."
            )
        raise ValueError(f"Unsupported chat mode for pedagogical instruction: {mode}")

    @staticmethod
    def _pick_confidence_hint(mode: ChatMode, *, has_context: bool) -> float:
        if mode == ChatMode.REFUSE_FULL_SOLUTION:
            return 0.96
        if mode == ChatMode.CLARIFY:
            return 0.42
        if mode == ChatMode.CODE_FEEDBACK:
            return 0.73
        if mode in (ChatMode.CONCEPT_EXPLAINER, ChatMode.HINT_ONLY):
            return 0.84 if has_context else 0.58
        return 0.55

    @staticmethod
    def _pick_response_template(mode: ChatMode, level: int) -> str | None:
        if mode == ChatMode.HINT_ONLY:
            return HINT_ONLY_RESPONSE_TEMPLATES.get(level)
        return _MODE_TEMPLATES.get(mode)

    @staticmethod
    def _pick_response_template_variables(mode: ChatMode) -> dict[str, str]:
        if mode == ChatMode.CLARIFY:
            return {
                "reason": "не хватает условия задачи или текущего шага",
                "requested_context": "условие задачи, номер задания или свой текущий код",
            }
        if mode == ChatMode.REFUSE_FULL_SOLUTION:
            return {
                "refusal_reason": "Это не поможет тебе в обучении.",
            }
        return {}
