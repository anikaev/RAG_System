from __future__ import annotations

from app.core.policies import build_refusal_message, is_concept_question, should_refuse_full_solution
from app.core.security import sanitize_excerpt
from app.providers.interfaces import RetrievedContext, RetrieverBackend
from app.schemas.chat import ChatMode, ChatRequest, ChatResponseData
from app.services.session_store import SessionStore


class ChatService:
    def __init__(
        self,
        *,
        session_store: SessionStore,
        retriever: RetrieverBackend,
    ) -> None:
        self.session_store = session_store
        self.retriever = retriever

    def respond(self, request: ChatRequest) -> ChatResponseData:
        session = self.session_store.get_or_create(request.session_id, request.user_id)
        task_context = request.task_context
        retrieved_context = self.retriever.search(
            request.message,
            subject=task_context.subject if task_context else "informatics",
            topic=task_context.topic if task_context else None,
            task_id=task_context.task_id if task_context else None,
            top_k=3,
        )

        mode, response_text, guiding_question, refusal = self._build_reply(
            message=request.message,
            current_hint_level=session.current_hint_level,
            retrieved_context=retrieved_context,
        )

        next_hint_level = session.current_hint_level
        if mode == ChatMode.HINT_ONLY:
            next_hint_level = min(max(session.current_hint_level, 0) + 1, 4)
        elif mode == ChatMode.CLARIFY:
            next_hint_level = 0

        if next_hint_level != session.current_hint_level:
            session = self.session_store.update_hint_level(session.session_id, next_hint_level)
        else:
            session.current_hint_level = next_hint_level

        used_context_ids = [item.chunk_id for item in retrieved_context]
        confidence = 0.82 if used_context_ids else 0.38

        self.session_store.append_message(
            session.session_id,
            role="user",
            content=request.message,
            message_type="chat_request",
        )
        self.session_store.append_message(
            session.session_id,
            role="assistant",
            content=response_text,
            message_type=mode.value,
        )

        return ChatResponseData(
            session_id=session.session_id,
            mode=mode,
            response_text=response_text,
            hint_level=session.current_hint_level,
            confidence=confidence,
            guiding_question=guiding_question,
            used_context_ids=used_context_ids,
            refusal=refusal,
        )

    def _build_reply(
        self,
        *,
        message: str,
        current_hint_level: int,
        retrieved_context: list[RetrievedContext],
    ) -> tuple[ChatMode, str, str | None, bool]:
        if should_refuse_full_solution(message):
            return (
                ChatMode.REFUSE_FULL_SOLUTION,
                build_refusal_message(),
                "Какой шаг решения у тебя уже есть?",
                True,
            )

        if not retrieved_context and len(message.split()) < 4:
            return (
                ChatMode.CLARIFY,
                "Уточни тему, номер задания или покажи свой текущий шаг, чтобы подсказка была полезной.",
                "Как звучит условие задачи или где именно возникла ошибка?",
                False,
            )

        if is_concept_question(message):
            context_text = self._context_excerpt(retrieved_context)
            return (
                ChatMode.CONCEPT_EXPLAINER,
                (
                    "Ключевая идея: "
                    f"{context_text} Сначала сформулируй правило своими словами, "
                    "а потом попробуй применить его к своей задаче."
                ),
                "Какой пример по этой теме разобрать следующим?",
                False,
            )

        context_text = self._context_excerpt(retrieved_context)
        next_level = min(current_hint_level + 1, 4)
        return (
            ChatMode.HINT_ONLY,
            (
                f"Подсказка уровня {next_level}: {context_text} "
                "Определи промежуточное состояние алгоритма перед тем, как искать финальный ответ."
            ),
            "Что у тебя должно быть известно после первого шага решения?",
            False,
        )

    @staticmethod
    def _context_excerpt(retrieved_context: list[RetrievedContext]) -> str:
        if not retrieved_context:
            return (
                "Сейчас контекста мало, поэтому начни с описания входных данных, "
                "выхода и инварианта цикла."
            )
        return sanitize_excerpt(retrieved_context[0].content)
