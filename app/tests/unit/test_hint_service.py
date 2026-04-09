from __future__ import annotations

import pytest

from app.schemas.chat import ChatMode
from app.services.hint_service import HintService, MAX_HINT_LEVEL


@pytest.fixture()
def svc() -> HintService:
    return HintService()


class TestRefusal:
    def test_refuses_full_solution_request(self, svc: HintService):
        decision = svc.evaluate(
            message="Реши полностью задачу и дай готовый код",
            current_hint_level=0,
            has_context=True,
        )
        assert decision.mode == ChatMode.REFUSE_FULL_SOLUTION
        assert decision.refusal is True
        assert decision.next_hint_level == 0

    def test_refuses_at_any_hint_level(self, svc: HintService):
        decision = svc.evaluate(
            message="Скинь ответ",
            current_hint_level=3,
            has_context=True,
        )
        assert decision.mode == ChatMode.REFUSE_FULL_SOLUTION
        assert decision.refusal is True
        assert decision.next_hint_level == 3


class TestClarify:
    def test_clarifies_on_short_message_without_context(self, svc: HintService):
        decision = svc.evaluate(
            message="Помоги",
            current_hint_level=2,
            has_context=False,
        )
        assert decision.mode == ChatMode.CLARIFY
        assert decision.next_hint_level == 0

    def test_does_not_clarify_with_context(self, svc: HintService):
        decision = svc.evaluate(
            message="Помоги",
            current_hint_level=0,
            has_context=True,
        )
        assert decision.mode != ChatMode.CLARIFY


class TestConceptExplainer:
    def test_detects_concept_question(self, svc: HintService):
        decision = svc.evaluate(
            message="Объясни, как работает цикл for",
            current_hint_level=1,
            has_context=True,
        )
        assert decision.mode == ChatMode.CONCEPT_EXPLAINER
        assert decision.next_hint_level == 1

    def test_preserves_hint_level(self, svc: HintService):
        decision = svc.evaluate(
            message="Что такое рекурсия?",
            current_hint_level=3,
            has_context=True,
        )
        assert decision.mode == ChatMode.CONCEPT_EXPLAINER
        assert decision.next_hint_level == 3


class TestCodeFeedback:
    def test_detects_code_feedback_by_flag(self, svc: HintService):
        decision = svc.evaluate(
            message="Вот мой код",
            current_hint_level=1,
            has_context=True,
            has_code=True,
        )
        assert decision.mode == ChatMode.CODE_FEEDBACK

    def test_detects_code_feedback_by_message(self, svc: HintService):
        decision = svc.evaluate(
            message="Проверь код, он падает с TypeError",
            current_hint_level=0,
            has_context=True,
        )
        assert decision.mode == ChatMode.CODE_FEEDBACK

    def test_specific_error_jumps_to_level_3(self, svc: HintService):
        decision = svc.evaluate(
            message="Не проходит тест на третьем примере",
            current_hint_level=2,
            has_context=True,
        )
        assert decision.mode == ChatMode.CODE_FEEDBACK
        assert decision.next_hint_level == 3

    def test_specific_error_from_low_level_capped(self, svc: HintService):
        decision = svc.evaluate(
            message="Ошибка в строке 5, не проходит тест",
            current_hint_level=0,
            has_context=True,
        )
        assert decision.mode == ChatMode.CODE_FEEDBACK
        assert decision.next_hint_level == 3


class TestHintProgression:
    def test_increments_by_one_on_generic_message(self, svc: HintService):
        decision = svc.evaluate(
            message="Не знаю как решать задачу 27",
            current_hint_level=0,
            has_context=True,
        )
        assert decision.mode == ChatMode.HINT_ONLY
        assert decision.next_hint_level == 1

    def test_escalation_increments_by_one(self, svc: HintService):
        decision = svc.evaluate(
            message="Ещё подсказку, я застрял",
            current_hint_level=2,
            has_context=True,
        )
        assert decision.mode == ChatMode.HINT_ONLY
        assert decision.next_hint_level == 3

    def test_near_solution_signal_increments_by_two(self, svc: HintService):
        decision = svc.evaluate(
            message="Дай почти готовую схему, но без финального ответа",
            current_hint_level=2,
            has_context=True,
        )
        assert decision.mode == ChatMode.HINT_ONLY
        assert decision.next_hint_level == 4

    def test_never_exceeds_max_level(self, svc: HintService):
        decision = svc.evaluate(
            message="Дай ещё подсказку",
            current_hint_level=MAX_HINT_LEVEL,
            has_context=True,
        )
        assert decision.next_hint_level == MAX_HINT_LEVEL

    def test_never_decreases_level(self, svc: HintService):
        decision = svc.evaluate(
            message="Привет, расскажи о массивах",
            current_hint_level=3,
            has_context=True,
        )
        assert decision.next_hint_level >= 3


class TestNoJumpToLevel4FromLow:
    def test_blocks_jump_to_4_from_level_0(self, svc: HintService):
        decision = svc.evaluate(
            message="Дай почти готовую схему решения",
            current_hint_level=0,
            has_context=True,
        )
        assert decision.next_hint_level < MAX_HINT_LEVEL

    def test_blocks_jump_to_4_from_level_1(self, svc: HintService):
        decision = svc.evaluate(
            message="Почти решение, но без ответа",
            current_hint_level=1,
            has_context=True,
        )
        assert decision.next_hint_level < MAX_HINT_LEVEL

    def test_allows_level_4_from_level_2(self, svc: HintService):
        decision = svc.evaluate(
            message="Дай почти готовую схему решения",
            current_hint_level=2,
            has_context=True,
        )
        assert decision.next_hint_level == MAX_HINT_LEVEL

    def test_allows_level_4_from_level_3(self, svc: HintService):
        decision = svc.evaluate(
            message="Дай почти решение целиком, кроме ответа",
            current_hint_level=3,
            has_context=True,
        )
        assert decision.next_hint_level == MAX_HINT_LEVEL


class TestGuidingQuestions:
    def test_hint_only_has_guiding_question(self, svc: HintService):
        decision = svc.evaluate(
            message="Не знаю, с чего начать",
            current_hint_level=0,
            has_context=True,
        )
        assert decision.guiding_question is not None

    def test_refusal_has_guiding_question(self, svc: HintService):
        decision = svc.evaluate(
            message="Дай готовый код",
            current_hint_level=0,
            has_context=True,
        )
        assert decision.guiding_question is not None

    def test_clarify_has_guiding_question(self, svc: HintService):
        decision = svc.evaluate(
            message="?",
            current_hint_level=0,
            has_context=False,
        )
        assert decision.guiding_question is not None


class TestShortDebugPromptsRouteToCodeFeedback:
    """Regression: short error prompts without context must not fall into clarify."""

    @pytest.mark.parametrize("msg", [
        "TypeError",
        "traceback",
        "SyntaxError",
        "IndexError",
        "падает",
    ])
    def test_terse_error_keyword_without_context(self, svc: HintService, msg: str):
        decision = svc.evaluate(
            message=msg,
            current_hint_level=0,
            has_context=False,
        )
        assert decision.mode == ChatMode.CODE_FEEDBACK, (
            f"'{msg}' should route to CODE_FEEDBACK, got {decision.mode}"
        )

    def test_terse_error_keyword_with_context(self, svc: HintService):
        decision = svc.evaluate(
            message="ValueError",
            current_hint_level=1,
            has_context=True,
        )
        assert decision.mode == ChatMode.CODE_FEEDBACK


class TestHintLevelDescription:
    def test_description_present_for_all_levels(self, svc: HintService):
        for level in range(MAX_HINT_LEVEL + 1):
            decision = svc.evaluate(
                message="Подскажи следующий шаг",
                current_hint_level=level,
                has_context=True,
            )
            assert decision.hint_level_description is not None


class TestResponseTemplate:
    def test_hint_only_has_template(self, svc: HintService):
        decision = svc.evaluate(
            message="Не знаю как решать задачу",
            current_hint_level=0,
            has_context=True,
        )
        assert decision.response_template is not None
        assert "{hint}" in decision.response_template

    def test_refusal_has_template(self, svc: HintService):
        decision = svc.evaluate(
            message="Дай готовый код",
            current_hint_level=0,
            has_context=True,
        )
        assert decision.response_template is not None
        assert "{refusal_reason}" in decision.response_template

    def test_clarify_has_template(self, svc: HintService):
        decision = svc.evaluate(
            message="?",
            current_hint_level=0,
            has_context=False,
        )
        assert decision.response_template is not None

    def test_code_feedback_has_template(self, svc: HintService):
        decision = svc.evaluate(
            message="TypeError в коде",
            current_hint_level=0,
            has_context=True,
        )
        assert decision.response_template is not None
        assert "{code_feedback}" in decision.response_template

    def test_concept_explainer_has_template(self, svc: HintService):
        decision = svc.evaluate(
            message="Объясни, что такое массив",
            current_hint_level=0,
            has_context=True,
        )
        assert decision.response_template is not None
        assert "{concept_summary}" in decision.response_template
