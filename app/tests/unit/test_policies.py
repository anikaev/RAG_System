from __future__ import annotations

from app.core.policies import (
    has_escalation_signal,
    has_near_solution_signal,
    has_specific_error_signal,
    is_code_feedback_request,
    is_concept_question,
    should_refuse_full_solution,
    wants_stronger_hints,
)


def test_should_refuse_full_solution_detects_direct_requests():
    assert should_refuse_full_solution("Реши полностью задачу и дай готовый код") is True
    assert should_refuse_full_solution("Помоги разобраться с идеей") is False


def test_is_concept_question_detects_explanation_requests():
    assert is_concept_question("Объясни, как работает цикл for") is True
    assert is_concept_question("Проверь мой код") is False


def test_is_code_feedback_request_detects_code_related_signals():
    assert is_code_feedback_request("Проверь код, он падает с TypeError") is True
    assert is_code_feedback_request("Объясни, что такое префиксные суммы") is False


def test_has_specific_error_signal_detects_concrete_failure_states():
    assert has_specific_error_signal("У меня wrong answer на третьем тесте") is True
    assert has_specific_error_signal("Нужна подсказка по задаче") is False


def test_has_escalation_signal_detects_follow_up_help_requests():
    assert has_escalation_signal("Дай еще подсказку, я застрял") is True
    assert has_escalation_signal("Объясни тему с самого начала") is False


def test_wants_stronger_hints_detects_stronger_prompting():
    assert wants_stronger_hints("Дай более сильную подсказку, я не понимаю") is True
    assert wants_stronger_hints("Нужен только небольшой намек") is False


def test_has_near_solution_signal_detects_almost_solution_requests():
    assert has_near_solution_signal("Дай почти готовую схему, но без ответа") is True
    assert has_near_solution_signal("Подскажи первый шаг") is False
