from __future__ import annotations

import logging
import re

from app.providers.interfaces import (
    LLMGenerationRequest,
    RetrievedContext,
    RetrieverBackend,
)
from app.schemas.chat import ChatMode, ChatRequest, ChatResponseData
from app.schemas.code import CodeCheckRequest, CodeCheckResponseData, SupportedLanguage
from app.services.code_service import CodeService
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
        code_service: CodeService,
    ) -> None:
        self.session_store = session_store
        self.llm_service = llm_service
        self.retriever = retriever
        self.hint_service = hint_service
        self.code_service = code_service

    def handle(self, request: ChatRequest) -> ChatResponseData:
        session = self.session_store.get_or_create(
            request.session_id, request.user_id,
        )

        retrieved_context = self._retrieve(request)
        extracted_code = self._extract_code(request.message)
        has_code = extracted_code is not None

        decision = self.hint_service.evaluate(
            message=request.message,
            current_hint_level=session.current_hint_level,
            has_context=bool(retrieved_context),
            has_code=has_code,
            session_id=session.session_id,
        )

        llm_context = retrieved_context
        if decision.mode == ChatMode.CODE_FEEDBACK and extracted_code is not None:
            llm_context = self._augment_with_code_feedback(
                request=request,
                code=extracted_code,
                retrieved_context=retrieved_context,
            )

        session = self._sync_hint_level(session, decision)

        llm_result = self.llm_service.generate(
            LLMGenerationRequest(
                user_message=request.message,
                mode=decision.mode.value,
                hint_level=decision.next_hint_level,
                refusal=decision.refusal,
                context=llm_context,
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
            "orchestrator.response",
            extra={
                "event": "orchestrator.response",
                "session_id": session.session_id,
                "mode": decision.mode.value,
                "hint_level": decision.next_hint_level,
                "confidence": round(llm_result.confidence, 3),
                "used_context_count": len(used_context_ids),
            },
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
            llm_provider=self._metadata_str(llm_result.metadata, "provider"),
            llm_primary_provider=self._metadata_str(
                llm_result.metadata,
                "primary_provider",
            ),
            llm_fallback_used=bool(llm_result.metadata.get("fallback_used", False)),
            llm_fallback_reason=self._metadata_str(
                llm_result.metadata,
                "fallback_reason",
            ),
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
    def _extract_code(message: str) -> str | None:
        match = _CODE_BLOCK_RE.search(message)
        if match:
            block = match.group(0)
            stripped = re.sub(r"^```[A-Za-z0-9_+-]*\n?", "", block)
            stripped = re.sub(r"\n?```$", "", stripped)
            normalized = stripped.strip()
            return normalized or None
        if _INLINE_CODE_LIKE_RE.search(message):
            normalized = message.strip()
            return normalized or None
        return None

    def _augment_with_code_feedback(
        self,
        *,
        request: ChatRequest,
        code: str,
        retrieved_context: list[RetrievedContext],
    ) -> list[RetrievedContext]:
        code_result = self.code_service.analyze_code(
            CodeCheckRequest(
                session_id=request.session_id,
                user_id=request.user_id,
                language=SupportedLanguage.PYTHON,
                code=code,
                task_id=request.task_context.task_id if request.task_context else None,
            )
        )
        code_context = RetrievedContext(
            chunk_id="code_check:summary",
            content=self._build_code_feedback_context(code_result),
            score=1.0,
            metadata={"source": "code_check", "mode": "code_feedback"},
        )
        return [code_context, *retrieved_context]

    @staticmethod
    def _build_code_feedback_context(code_result: CodeCheckResponseData) -> str:
        issue_summaries = "; ".join(
            f"{item.code}: {item.message}"
            for item in code_result.issues
        )
        parts = [
            code_result.feedback_text,
            (
                "Статус: "
                f"accepted={code_result.accepted}, "
                f"syntax_ok={code_result.summary.syntax_ok}, "
                f"execution_status={code_result.summary.execution_status.value}, "
                f"public_tests={code_result.summary.public_tests_passed}/{code_result.summary.public_tests_total}, "
                f"hidden_tests={code_result.summary.hidden_tests_summary}."
            ),
        ]
        if issue_summaries:
            parts.append(f"Проблемы: {issue_summaries}.")
        return " ".join(parts)

    @staticmethod
    def _metadata_str(metadata: dict[str, object], key: str) -> str | None:
        value = metadata.get(key)
        if value is None:
            return None
        text = str(value).strip()
        return text or None
