from __future__ import annotations

from app.core.policies import is_concept_question, should_refuse_full_solution
from app.providers.interfaces import (
    LLMGenerationRequest,
    LLMProvider,
    RetrievedContext,
    RetrieverBackend,
)
from app.schemas.chat import ChatMode, ChatRequest, ChatResponseData
from app.services.session_store import SessionStore


class ChatService:
    def __init__(
        self,
        *,
        session_store: SessionStore,
        llm_provider: LLMProvider,
        retriever: RetrieverBackend,
    ) -> None:
        self.session_store = session_store
        self.llm_provider = llm_provider
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

        mode, next_hint_level, refusal = self._select_mode(
            message=request.message,
            current_hint_level=session.current_hint_level,
            retrieved_context=retrieved_context,
        )

        if next_hint_level != session.current_hint_level:
            session = self.session_store.update_hint_level(session.session_id, next_hint_level)
        else:
            session.current_hint_level = next_hint_level

        llm_result = self.llm_provider.generate(
            LLMGenerationRequest(
                user_message=request.message,
                mode=mode.value,
                hint_level=next_hint_level,
                refusal=refusal,
                context=retrieved_context,
            )
        )

        used_context_ids = [item.chunk_id for item in retrieved_context]

        self.session_store.append_message(
            session.session_id,
            role="user",
            content=request.message,
            message_type="chat_request",
        )
        self.session_store.append_message(
            session.session_id,
            role="assistant",
            content=llm_result.response_text,
            message_type=mode.value,
        )

        return ChatResponseData(
            session_id=session.session_id,
            mode=mode,
            response_text=llm_result.response_text,
            hint_level=session.current_hint_level,
            confidence=llm_result.confidence,
            guiding_question=llm_result.guiding_question,
            used_context_ids=used_context_ids,
            refusal=refusal,
        )

    def _select_mode(
        self,
        *,
        message: str,
        current_hint_level: int,
        retrieved_context: list[RetrievedContext],
    ) -> tuple[ChatMode, int, bool]:
        if should_refuse_full_solution(message):
            return ChatMode.REFUSE_FULL_SOLUTION, current_hint_level, True

        if not retrieved_context and len(message.split()) < 4:
            return ChatMode.CLARIFY, 0, False

        if is_concept_question(message):
            return ChatMode.CONCEPT_EXPLAINER, current_hint_level, False

        next_level = min(current_hint_level + 1, 4)
        return ChatMode.HINT_ONLY, next_level, False
