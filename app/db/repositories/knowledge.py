from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import KnowledgeChunk


class KnowledgeChunkRepository:
    def count(self, db: Session) -> int:
        stmt = select(func.count(KnowledgeChunk.id))
        return int(db.execute(stmt).scalar_one())

    def get_by_chunk_id(self, db: Session, chunk_id: str) -> KnowledgeChunk | None:
        stmt = select(KnowledgeChunk).where(KnowledgeChunk.chunk_id == chunk_id)
        return db.execute(stmt).scalar_one_or_none()

    def list_for_retrieval(
        self,
        db: Session,
        *,
        subject: str | None = None,
        topic: str | None = None,
        task_id: str | None = None,
    ) -> list[KnowledgeChunk]:
        stmt = select(KnowledgeChunk)
        if subject is not None:
            stmt = stmt.where(KnowledgeChunk.subject == subject)
        if topic is not None:
            stmt = stmt.where(KnowledgeChunk.topic == topic)
        if task_id is not None:
            stmt = stmt.where(KnowledgeChunk.task_id == task_id)
        stmt = stmt.order_by(KnowledgeChunk.chunk_id.asc())
        return list(db.execute(stmt).scalars().all())

    def upsert(
        self,
        db: Session,
        *,
        chunk_id: str,
        source_id: str,
        subject: str,
        topic: str | None,
        task_id: str | None,
        content: str,
        metadata_json: dict[str, str],
        embedding_json: list[float] | None = None,
    ) -> KnowledgeChunk:
        record = self.get_by_chunk_id(db, chunk_id)
        if record is None:
            record = KnowledgeChunk(
                chunk_id=chunk_id,
                source_id=source_id,
                subject=subject,
                topic=topic,
                task_id=task_id,
                content=content,
                metadata_json=metadata_json,
                embedding_json=embedding_json,
            )
            db.add(record)
        else:
            record.source_id = source_id
            record.subject = subject
            record.topic = topic
            record.task_id = task_id
            record.content = content
            record.metadata_json = metadata_json
            record.embedding_json = embedding_json
        db.flush()
        return record
