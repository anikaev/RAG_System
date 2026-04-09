from __future__ import annotations

from app.providers.interfaces import LLMProvider, RetrieverBackend
from app.schemas.chat import ChatRequest, ChatResponseData
from app.services.dialogue_orchestrator import DialogueOrchestrator
from app.services.hint_service import HintService
from app.services.session_store import SessionStore


class ChatService:
    """Thin facade that delegates to DialogueOrchestrator.

    Kept for backward-compatibility with existing route wiring and tests.
    """

    def __init__(
        self,
        *,
        session_store: SessionStore,
        llm_provider: LLMProvider,
        retriever: RetrieverBackend,
        hint_service: HintService,
    ) -> None:
        self._orchestrator = DialogueOrchestrator(
            session_store=session_store,
            llm_provider=llm_provider,
            retriever=retriever,
            hint_service=hint_service,
        )

    @property
    def orchestrator(self) -> DialogueOrchestrator:
        return self._orchestrator

    def respond(self, request: ChatRequest) -> ChatResponseData:
        return self._orchestrator.handle(request)
