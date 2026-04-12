from __future__ import annotations

import logging
import re

from app.providers.interfaces import (
    LLMGenerationRequest,
    RetrievedContext,
    RetrieverBackend,
)
from app.schemas.chat import ChatMode, ChatRequest, ChatResponseData
from app.services.hint_service import HintDecision, HintService
from app.services.llm_service import LLMService
from app.services.session_store import SessionRecord, SessionStore

logger = logging.getLogger(__name__)

_CODE_BLOCK_RE = re.compile(r"```[\s\S]+?```")
_INLINE_CODE_LIKE_RE = re.compile(
    r"(?:def |class |import |for .+ in |while |if .+:)"
)


class DialogueOrchestrator:
    """Central business-logic coordinator.

    Accepts a ChatRequest, runs intent classification, retrieval,
    HintService evaluation, LLM generation, and persists the dialogue
    history — returning a fully-formed ChatResponseData.
    """

    def __init__(
        self,
        *,
        session_store: SessionStore,
        llm_service: LLMService,
        retriever: RetrieverBackend,
        hint_service: HintService,
    ) -> None:
        self.session_store = session_store
        self.llm_service = llm_service
        self.retriever = retriever
        self.hint_service = hint_service

    def handle(self, request: ChatRequest) -> ChatResponseData:
        session = self.session_store.get_or_create(
            request.session_id, request.user_id,
        )

        retrieved_context = self._retrieve(request)
        has_code = self._message_contains_code(request.message)

        decision = self.hint_service.evaluate(
            message=request.message,
            current_hint_level=session.current_hint_level,
            has_context=bool(retrieved_context),
            has_code=has_code,
        )

        session = self._sync_hint_level(session, decision)

        llm_result = self.llm_service.generate(
            LLMGenerationRequest(
                user_message=request.message,
                mode=decision.mode.value,
                hint_level=decision.next_hint_level,
                refusal=decision.refusal,
                context=retrieved_context,
                pedagogical_instruction=decision.pedagogical_instruction,
                hint_level_description=decision.hint_level_description,
                response_template=decision.response_template,
                response_template_variables=decision.response_template_variables,
                guiding_question_hint=decision.guiding_question,
                confidence_hint=decision.confidence_hint,
            )
        )

        used_context_ids = [ctx.chunk_id for ctx in retrieved_context]

        self._persist_exchange(
            session_id=session.session_id,
            user_message=request.message,
            assistant_message=llm_result.response_text,
            mode=decision.mode,
        )

        logger.info(
            "orchestrator.response session=%s mode=%s hint=%d confidence=%.2f",
            session.session_id,
            decision.mode.value,
            decision.next_hint_level,
            llm_result.confidence,
        )

        return ChatResponseData(
            session_id=session.session_id,
            mode=decision.mode,
            response_text=llm_result.response_text,
            hint_level=decision.next_hint_level,
            confidence=llm_result.confidence,
            guiding_question=llm_result.guiding_question or decision.guiding_question,
            used_context_ids=used_context_ids,
            refusal=decision.refusal,
        )

    def _retrieve(self, request: ChatRequest) -> list[RetrievedContext]:
        tc = request.task_context
        return self.retriever.search(
            request.message,
            subject=tc.subject if tc else "informatics",
            topic=tc.topic if tc else None,
            task_id=tc.task_id if tc else None,
            top_k=3,
        )

    def _sync_hint_level(
        self,
        session: SessionRecord,
        decision: HintDecision,
    ) -> SessionRecord:
        if decision.next_hint_level != session.current_hint_level:
            return self.session_store.update_hint_level(
                session.session_id, decision.next_hint_level,
            )
        return session

    def _persist_exchange(
        self,
        *,
        session_id: str,
        user_message: str,
        assistant_message: str,
        mode: ChatMode,
    ) -> None:
        self.session_store.append_message(
            session_id,
            role="user",
            content=user_message,
            message_type="chat_request",
        )
        self.session_store.append_message(
            session_id,
            role="assistant",
            content=assistant_message,
            message_type=mode.value,
        )

    @staticmethod
    def _message_contains_code(message: str) -> bool:
        if _CODE_BLOCK_RE.search(message):
            return True
        return bool(_INLINE_CODE_LIKE_RE.search(message))
