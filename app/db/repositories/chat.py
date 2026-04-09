from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import ChatMessage, ChatSession


class ChatSessionRepository:
    def get_by_session_id(self, db: Session, session_id: str) -> ChatSession | None:
        stmt = select(ChatSession).where(ChatSession.session_id == session_id)
        return db.execute(stmt).scalar_one_or_none()

    def get_or_create(
        self,
        db: Session,
        *,
        session_id: str | None,
        user_id: str | None,
    ) -> ChatSession:
        resolved_session_id = session_id or str(uuid4())
        existing = self.get_by_session_id(db, resolved_session_id)
        if existing is not None:
            if user_id and existing.user_id is None:
                existing.user_id = user_id
            existing.updated_at = datetime.now(UTC)
            db.flush()
            return existing

        record = ChatSession(
            session_id=resolved_session_id,
            user_id=user_id,
            current_hint_level=0,
        )
        db.add(record)
        db.flush()
        return record

    def update_hint_level(self, db: Session, *, session_id: str, hint_level: int) -> ChatSession:
        session = self.get_by_session_id(db, session_id)
        if session is None:
            raise LookupError(f"Session not found: {session_id}")
        session.current_hint_level = hint_level
        session.updated_at = datetime.now(UTC)
        db.flush()
        return session


class ChatMessageRepository:
    def create(
        self,
        db: Session,
        *,
        session_id: str,
        role: str,
        content: str,
        message_type: str,
    ) -> ChatMessage:
        record = ChatMessage(
            session_id=session_id,
            role=role,
            content=content,
            message_type=message_type,
            created_at=datetime.now(UTC),
        )
        db.add(record)
        db.flush()
        return record

    def list_for_session(self, db: Session, *, session_id: str) -> list[ChatMessage]:
        stmt = (
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at.asc(), ChatMessage.id.asc())
        )
        return list(db.execute(stmt).scalars())
