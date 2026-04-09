from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Protocol
from threading import RLock
from uuid import uuid4

from app.db.repositories import ChatMessageRepository, ChatSessionRepository
from app.db.session import DatabaseSessionManager


@dataclass(slots=True)
class StoredMessage:
    role: str
    content: str
    message_type: str
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(slots=True)
class SessionRecord:
    session_id: str
    user_id: str | None
    current_hint_level: int = 0
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    history: list[StoredMessage] = field(default_factory=list)


class SessionStore(Protocol):
    def get_or_create(self, session_id: str | None, user_id: str | None) -> SessionRecord:
        ...

    def append_message(
        self,
        session_id: str,
        *,
        role: str,
        content: str,
        message_type: str,
    ) -> None:
        ...

    def get_history(self, session_id: str) -> list[StoredMessage]:
        ...

    def update_hint_level(self, session_id: str, hint_level: int) -> SessionRecord:
        ...


class InMemorySessionStore(SessionStore):
    def __init__(self) -> None:
        self._lock = RLock()
        self._sessions: dict[str, SessionRecord] = {}

    def get_or_create(self, session_id: str | None, user_id: str | None) -> SessionRecord:
        with self._lock:
            resolved_session_id = session_id or str(uuid4())
            session = self._sessions.get(resolved_session_id)
            if session is None:
                session = SessionRecord(session_id=resolved_session_id, user_id=user_id)
                self._sessions[resolved_session_id] = session
            elif user_id and session.user_id is None:
                session.user_id = user_id
            session.updated_at = datetime.now(UTC)
            return session

    def append_message(
        self,
        session_id: str,
        *,
        role: str,
        content: str,
        message_type: str,
    ) -> None:
        with self._lock:
            session = self._sessions[session_id]
            session.history.append(
                StoredMessage(role=role, content=content, message_type=message_type)
            )
            session.updated_at = datetime.now(UTC)

    def get_history(self, session_id: str) -> list[StoredMessage]:
        with self._lock:
            session = self._sessions[session_id]
            return list(session.history)

    def update_hint_level(self, session_id: str, hint_level: int) -> SessionRecord:
        with self._lock:
            session = self._sessions[session_id]
            session.current_hint_level = hint_level
            session.updated_at = datetime.now(UTC)
            return session


class DatabaseSessionStore(SessionStore):
    def __init__(self, db_manager: DatabaseSessionManager) -> None:
        self.db_manager = db_manager
        self.session_repository = ChatSessionRepository()
        self.message_repository = ChatMessageRepository()

    def get_or_create(self, session_id: str | None, user_id: str | None) -> SessionRecord:
        with self.db_manager.session_scope() as db:
            session = self.session_repository.get_or_create(
                db,
                session_id=session_id,
                user_id=user_id,
            )
            history = self.message_repository.list_for_session(db, session_id=session.session_id)
            return SessionRecord(
                session_id=session.session_id,
                user_id=session.user_id,
                current_hint_level=session.current_hint_level,
                created_at=session.created_at,
                updated_at=session.updated_at,
                history=[
                    StoredMessage(
                        role=item.role,
                        content=item.content,
                        message_type=item.message_type,
                        created_at=item.created_at,
                    )
                    for item in history
                ],
            )

    def append_message(
        self,
        session_id: str,
        *,
        role: str,
        content: str,
        message_type: str,
    ) -> None:
        with self.db_manager.session_scope() as db:
            self.message_repository.create(
                db,
                session_id=session_id,
                role=role,
                content=content,
                message_type=message_type,
            )

    def get_history(self, session_id: str) -> list[StoredMessage]:
        with self.db_manager.session_scope() as db:
            history = self.message_repository.list_for_session(db, session_id=session_id)
            return [
                StoredMessage(
                    role=item.role,
                    content=item.content,
                    message_type=item.message_type,
                    created_at=item.created_at,
                )
                for item in history
            ]

    def update_hint_level(self, session_id: str, hint_level: int) -> SessionRecord:
        with self.db_manager.session_scope() as db:
            session = self.session_repository.update_hint_level(
                db,
                session_id=session_id,
                hint_level=hint_level,
            )
            return SessionRecord(
                session_id=session.session_id,
                user_id=session.user_id,
                current_hint_level=session.current_hint_level,
                created_at=session.created_at,
                updated_at=session.updated_at,
                history=[],
            )
