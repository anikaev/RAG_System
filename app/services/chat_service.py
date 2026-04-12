from __future__ import annotations

from app.providers.interfaces import RetrieverBackend
from app.schemas.chat import ChatRequest, ChatResponseData
from app.services.code_service import CodeService
from app.services.dialogue_orchestrator import DialogueOrchestrator
from app.services.hint_service import HintService
from app.services.llm_service import LLMService
from app.services.session_store import SessionStore


class ChatService:
    """Thin facade that delegates to DialogueOrchestrator.

    Kept for backward-compatibility with existing route wiring and tests.
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
        self._orchestrator = DialogueOrchestrator(
            session_store=session_store,
            llm_service=llm_service,
            retriever=retriever,
            hint_service=hint_service,
            code_service=code_service,
        )

    @property
    def orchestrator(self) -> DialogueOrchestrator:
        return self._orchestrator

    def respond(self, request: ChatRequest) -> ChatResponseData:
        return self._orchestrator.handle(request)
