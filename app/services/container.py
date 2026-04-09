from __future__ import annotations

import logging
from dataclasses import dataclass

from app.core.config import Settings
from app.db.bootstrap import seed_knowledge_chunks
from app.db.session import DatabaseSessionManager
from app.providers.factory import (
    build_code_execution_backend,
    build_embedding_provider,
    build_llm_provider,
    build_retriever_backend,
)
from app.providers.interfaces import CodeExecutionBackend, EmbeddingProvider, LLMProvider, RetrieverBackend
from app.services.chat_service import ChatService
from app.services.code_service import CodeService
from app.services.session_store import DatabaseSessionStore, InMemorySessionStore, SessionStore

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class ServiceContainer:
    session_store: SessionStore
    llm_provider: LLMProvider
    embedding_provider: EmbeddingProvider
    retriever: RetrieverBackend
    code_execution_backend: CodeExecutionBackend
    chat_service: ChatService
    code_service: CodeService
    db_manager: DatabaseSessionManager | None = None


def build_service_container(settings: Settings) -> ServiceContainer:
    embedding_provider = build_embedding_provider(settings)
    session_store, db_manager = _build_session_store(settings, embedding_provider)
    llm_provider = build_llm_provider(settings)
    retriever = build_retriever_backend(settings)
    code_backend = build_code_execution_backend(settings)

    return ServiceContainer(
        session_store=session_store,
        llm_provider=llm_provider,
        embedding_provider=embedding_provider,
        retriever=retriever,
        code_execution_backend=code_backend,
        chat_service=ChatService(
            session_store=session_store,
            llm_provider=llm_provider,
            retriever=retriever,
        ),
        code_service=CodeService(
            settings=settings,
            session_store=session_store,
            code_backend=code_backend,
        ),
        db_manager=db_manager,
    )


def _build_session_store(
    settings: Settings,
    embedding_provider: EmbeddingProvider,
) -> tuple[SessionStore, DatabaseSessionManager | None]:
    if settings.session_backend == "memory":
        return InMemorySessionStore(), None

    try:
        db_manager = DatabaseSessionManager(settings)
        db_manager.check_connection()
        if settings.database_bootstrap_schema:
            db_manager.create_schema()
        if settings.seed_demo_data_on_startup:
            seed_knowledge_chunks(
                db_manager,
                settings.kb_seed_path,
                embedding_provider=embedding_provider,
            )
        return DatabaseSessionStore(db_manager), db_manager
    except Exception as exc:
        if settings.session_backend == "database" or not settings.database_fallback_to_memory:
            raise
        logger.warning("db.unavailable_falling_back_to_memory error=%s", exc)
        return InMemorySessionStore(), None
