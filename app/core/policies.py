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
