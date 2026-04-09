from __future__ import annotations

FULL_SOLUTION_PATTERNS = (
    "реши за меня",
    "реши полностью",
    "полное решение",
    "дай готовый код",
    "дай ответ",
    "скинь ответ",
    "готовое решение",
)

CONCEPT_PATTERNS = (
    "объясни",
    "что такое",
    "как работает",
    "почему",
)

CODE_FEEDBACK_PATTERNS = (
    "ошибка",
    "traceback",
    "исключение",
    "падает",
    "не работает код",
    "проверь код",
    "посмотри код",
    "syntaxerror",
    "typeerror",
    "indexerror",
    "valueerror",
)

SPECIFIC_ERROR_PATTERNS = (
    "ошибка в строке",
    "не проходит тест",
    "неверный ответ",
    "runtime error",
    "wrong answer",
    "ошибка компиляции",
    "синтаксическая ошибка",
)

ESCALATION_PATTERNS = (
    "еще подсказку",
    "ещё подсказку",
    "следующую подсказку",
    "подскажи следующий шаг",
    "дай следующий шаг",
    "я запутался",
    "все еще не понимаю",
    "всё ещё не понимаю",
    "не понял",
    "не поняла",
    "застрял",
    "застряла",
)

STRONG_HINT_PATTERNS = (
    "дай подсказку",
    "дай сильнее",
    "дай более сильную подсказку",
    "почти готовую схему",
    "почти решение",
    "намек сильнее",
    "не понимаю",
    "не могу",
    "помоги",
    "я запутался",
)

NEAR_SOLUTION_PATTERNS = (
    "почти готовую схему",
    "почти решение",
    "почти готовое решение",
    "без ответа, но почти полностью",
)


def normalize_text(text: str) -> str:
    return " ".join(text.lower().split())


def should_refuse_full_solution(text: str) -> bool:
    normalized = normalize_text(text)
    return any(pattern in normalized for pattern in FULL_SOLUTION_PATTERNS)


def is_concept_question(text: str) -> bool:
    normalized = normalize_text(text)
    return any(pattern in normalized for pattern in CONCEPT_PATTERNS)


def build_refusal_message() -> str:
    return (
        "Я не выдаю готовое решение целиком. Могу помочь по шагам: "
        "разобрать идею, проверить промежуточный код или задать наводящий вопрос."
    )


def is_code_feedback_request(text: str) -> bool:
    normalized = normalize_text(text)
    return any(pattern in normalized for pattern in CODE_FEEDBACK_PATTERNS)


def has_specific_error_signal(text: str) -> bool:
    normalized = normalize_text(text)
    return any(pattern in normalized for pattern in SPECIFIC_ERROR_PATTERNS)


def has_escalation_signal(text: str) -> bool:
    normalized = normalize_text(text)
    return any(pattern in normalized for pattern in ESCALATION_PATTERNS)


def wants_stronger_hints(text: str) -> bool:
    normalized = normalize_text(text)
    return any(pattern in normalized for pattern in STRONG_HINT_PATTERNS)


def has_near_solution_signal(text: str) -> bool:
    normalized = normalize_text(text)
    return any(pattern in normalized for pattern in NEAR_SOLUTION_PATTERNS)
