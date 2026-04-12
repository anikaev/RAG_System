from __future__ import annotations

import pytest

from app.providers.interfaces import RetrievedContext
from app.providers.mock_llm_provider import MockLLMProvider
from app.schemas.chat import ChatMode, ChatRequest, TaskContext
from app.services.dialogue_orchestrator import DialogueOrchestrator
from app.services.hint_service import HintService
from app.services.llm_service import LLMService
from app.services.session_store import InMemorySessionStore


class StubRetriever:
    """Always returns a fixed context list for testing."""

    def __init__(self, chunks: list[RetrievedContext] | None = None) -> None:
        self._chunks = chunks or [
            RetrievedContext(
                chunk_id="stub-1",
                content="Массивы: последовательный перебор элементов.",
                score=0.9,
            ),
        ]

    def search(self, query, *, subject=None, topic=None, task_id=None, top_k=3):
        return self._chunks


class EmptyRetriever:
    def search(self, query, *, subject=None, topic=None, task_id=None, top_k=3):
        return []


def _build_orchestrator(
    retriever=None,
) -> DialogueOrchestrator:
    return DialogueOrchestrator(
        session_store=InMemorySessionStore(),
        llm_service=LLMService(primary_provider=MockLLMProvider()),
        retriever=retriever or StubRetriever(),
        hint_service=HintService(),
    )


class TestEndToEndModes:
    def test_concept_explainer_mode(self):
        orch = _build_orchestrator()
        result = orch.handle(ChatRequest(
            user_id="u1",
            message="Объясни, как работает цикл for в Python",
        ))
        assert result.mode == ChatMode.CONCEPT_EXPLAINER
        assert result.session_id
        assert result.confidence > 0

    def test_refuse_full_solution(self):
        orch = _build_orchestrator()
        result = orch.handle(ChatRequest(
            user_id="u1",
            message="Реши полностью задачу 27 и дай готовый код",
        ))
        assert result.mode == ChatMode.REFUSE_FULL_SOLUTION
        assert result.refusal is True
        assert "не выдаю готовое решение" in result.response_text.lower()

    def test_clarify_on_short_message_without_context(self):
        orch = _build_orchestrator(retriever=EmptyRetriever())
        result = orch.handle(ChatRequest(
            user_id="u1",
            message="Помоги",
        ))
        assert result.mode == ChatMode.CLARIFY
        assert result.hint_level == 0
        assert result.response_text.startswith("Пока контекста мало:")
        assert result.guiding_question == (
            "Что именно у тебя уже есть: условие, идея решения или фрагмент кода?"
        )

    def test_hint_only_generic_request(self):
        orch = _build_orchestrator()
        result = orch.handle(ChatRequest(
            user_id="u1",
            message="Не знаю как решать задачу 27 по массивам",
        ))
        assert result.mode == ChatMode.HINT_ONLY
        assert result.hint_level == 1

    def test_code_feedback_when_message_has_code(self):
        orch = _build_orchestrator()
        result = orch.handle(ChatRequest(
            user_id="u1",
            message="```python\nfor i in range(10):\n    print(i)\n```",
        ))
        assert result.mode == ChatMode.CODE_FEEDBACK

    def test_short_error_without_context_routes_to_code_feedback(self):
        orch = _build_orchestrator(retriever=EmptyRetriever())
        result = orch.handle(ChatRequest(
            user_id="u1",
            message="TypeError",
        ))
        assert result.mode == ChatMode.CODE_FEEDBACK
        assert "разбор кода" in result.response_text.lower()


class TestHintProgression:
    def test_hint_level_advances_across_turns(self):
        orch = _build_orchestrator()
        r1 = orch.handle(ChatRequest(
            user_id="u1",
            message="Не знаю как решать задачу 27",
        ))
        session_id = r1.session_id
        assert r1.hint_level == 1

        r2 = orch.handle(ChatRequest(
            session_id=session_id,
            user_id="u1",
            message="Дай ещё подсказку, я застрял",
        ))
        assert r2.hint_level == 2

        r3 = orch.handle(ChatRequest(
            session_id=session_id,
            user_id="u1",
            message="Следующую подсказку",
        ))
        assert r3.hint_level == 3

    def test_refusal_does_not_advance_hint_level(self):
        orch = _build_orchestrator()
        r1 = orch.handle(ChatRequest(
            user_id="u1",
            message="Не знаю как решать задачу 27",
        ))
        session_id = r1.session_id
        assert r1.hint_level == 1

        r2 = orch.handle(ChatRequest(
            session_id=session_id,
            user_id="u1",
            message="Дай готовый код",
        ))
        assert r2.mode == ChatMode.REFUSE_FULL_SOLUTION
        assert r2.hint_level == 1


class TestContextUsage:
    def test_used_context_ids_are_returned(self):
        orch = _build_orchestrator()
        result = orch.handle(ChatRequest(
            user_id="u1",
            message="Помоги с массивами",
            task_context=TaskContext(
                subject="informatics",
                topic="task_27",
            ),
        ))
        assert "stub-1" in result.used_context_ids

    def test_empty_context_with_long_message_gives_hint(self):
        orch = _build_orchestrator(retriever=EmptyRetriever())
        result = orch.handle(ChatRequest(
            user_id="u1",
            message="Я хочу решить задачу по массивам, помоги разобрать идею",
        ))
        assert result.mode == ChatMode.HINT_ONLY
        assert result.used_context_ids == []


class TestHistoryPersistence:
    def test_messages_stored_in_session(self):
        store = InMemorySessionStore()
        orch = DialogueOrchestrator(
            session_store=store,
            llm_service=LLMService(primary_provider=MockLLMProvider()),
            retriever=StubRetriever(),
            hint_service=HintService(),
        )
        result = orch.handle(ChatRequest(
            user_id="u1",
            message="Помоги с задачей",
        ))
        history = store.get_history(result.session_id)
        assert len(history) == 2
        assert history[0].role == "user"
        assert history[1].role == "assistant"


class TestGuidingQuestion:
    def test_response_includes_guiding_question(self):
        orch = _build_orchestrator()
        result = orch.handle(ChatRequest(
            user_id="u1",
            message="Не знаю как решать задачу 27",
        ))
        assert result.guiding_question is not None
        assert len(result.guiding_question) > 0
