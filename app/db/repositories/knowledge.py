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
                embedding_json=None,
            )
            db.add(record)
        else:
            record.source_id = source_id
            record.subject = subject
            record.topic = topic
            record.task_id = task_id
            record.content = content
            record.metadata_json = metadata_json
        db.flush()
        return record
