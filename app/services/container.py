from __future__ import annotations

import logging
from dataclasses import dataclass

from app.core.config import Settings
from app.db.bootstrap import seed_knowledge_chunks
from app.db.session import DatabaseSessionManager
from app.providers.fallback_retriever import FallbackRetriever
from app.providers.stub_code_runner import LocalStubCodeRunner
from app.services.chat_service import ChatService
from app.services.code_service import CodeService
from app.services.session_store import DatabaseSessionStore, InMemorySessionStore, SessionStore

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class ServiceContainer:
    session_store: SessionStore
    chat_service: ChatService
    code_service: CodeService
    db_manager: DatabaseSessionManager | None = None


def build_service_container(settings: Settings) -> ServiceContainer:
    session_store, db_manager = _build_session_store(settings)
    retriever = FallbackRetriever(settings.kb_seed_path)
    code_backend = LocalStubCodeRunner()

    return ServiceContainer(
        session_store=session_store,
        chat_service=ChatService(
            session_store=session_store,
            retriever=retriever,
        ),
        code_service=CodeService(
            settings=settings,
            session_store=session_store,
            code_backend=code_backend,
        ),
        db_manager=db_manager,
    )


def _build_session_store(settings: Settings) -> tuple[SessionStore, DatabaseSessionManager | None]:
    if settings.session_backend == "memory":
        return InMemorySessionStore(), None

    try:
        db_manager = DatabaseSessionManager(settings)
        db_manager.check_connection()
        if settings.database_bootstrap_schema:
            db_manager.create_schema()
        if settings.seed_demo_data_on_startup:
            seed_knowledge_chunks(db_manager, settings.kb_seed_path)
        return DatabaseSessionStore(db_manager), db_manager
    except Exception as exc:
        if settings.session_backend == "database" or not settings.database_fallback_to_memory:
            raise
        logger.warning("db.unavailable_falling_back_to_memory error=%s", exc)
        return InMemorySessionStore(), None
