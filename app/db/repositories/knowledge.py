from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import KnowledgeChunk, KnowledgeDocument


class KnowledgeChunkRepository:
    def count(self, db: Session) -> int:
        stmt = select(func.count(KnowledgeChunk.id))
        return int(db.execute(stmt).scalar_one())

    def get_by_chunk_id(self, db: Session, chunk_id: str) -> KnowledgeChunk | None:
        stmt = select(KnowledgeChunk).where(KnowledgeChunk.chunk_id == chunk_id)
        return db.execute(stmt).scalar_one_or_none()

    def list_for_document(self, db: Session, document_id: str) -> list[KnowledgeChunk]:
        stmt = (
            select(KnowledgeChunk)
            .where(KnowledgeChunk.document_id == document_id)
            .order_by(KnowledgeChunk.chunk_id.asc())
        )
        return list(db.execute(stmt).scalars().all())

    def count_for_document(self, db: Session, document_id: str) -> int:
        stmt = select(func.count(KnowledgeChunk.id)).where(
            KnowledgeChunk.document_id == document_id
        )
        return int(db.execute(stmt).scalar_one())

    def delete_for_document(self, db: Session, document_id: str) -> int:
        rows = self.list_for_document(db, document_id)
        for row in rows:
            db.delete(row)
        db.flush()
        return len(rows)

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
        document_id: str | None,
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
                document_id=document_id,
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
            record.document_id = document_id
            record.source_id = source_id
            record.subject = subject
            record.topic = topic
            record.task_id = task_id
            record.content = content
            record.metadata_json = metadata_json
            record.embedding_json = embedding_json
        db.flush()
        return record


class KnowledgeDocumentRepository:
    def count(self, db: Session) -> int:
        stmt = select(func.count(KnowledgeDocument.id))
        return int(db.execute(stmt).scalar_one())

    def get_by_document_id(
        self,
        db: Session,
        document_id: str,
    ) -> KnowledgeDocument | None:
        stmt = select(KnowledgeDocument).where(
            KnowledgeDocument.document_id == document_id
        )
        return db.execute(stmt).scalar_one_or_none()

    def list_with_chunk_counts(
        self,
        db: Session,
    ) -> list[tuple[KnowledgeDocument, int]]:
        stmt = (
            select(
                KnowledgeDocument,
                func.count(KnowledgeChunk.id),
            )
            .outerjoin(
                KnowledgeChunk,
                KnowledgeChunk.document_id == KnowledgeDocument.document_id,
            )
            .group_by(KnowledgeDocument.id)
            .order_by(KnowledgeDocument.updated_at.desc())
        )
        return [
            (document, int(chunk_count))
            for document, chunk_count in db.execute(stmt).all()
        ]

    def upsert(
        self,
        db: Session,
        *,
        document_id: str,
        title: str,
        source_type: str,
        source_uri: str | None,
        original_filename: str | None,
        subject: str,
        topic: str | None,
        task_id: str | None,
        status: str,
        content_raw: str,
        metadata_json: dict[str, str],
    ) -> KnowledgeDocument:
        record = self.get_by_document_id(db, document_id)
        if record is None:
            record = KnowledgeDocument(
                document_id=document_id,
                title=title,
                source_type=source_type,
                source_uri=source_uri,
                original_filename=original_filename,
                subject=subject,
                topic=topic,
                task_id=task_id,
                status=status,
                content_raw=content_raw,
                metadata_json=metadata_json,
            )
            db.add(record)
        else:
            record.title = title
            record.source_type = source_type
            record.source_uri = source_uri
            record.original_filename = original_filename
            record.subject = subject
            record.topic = topic
            record.task_id = task_id
            record.status = status
            record.content_raw = content_raw
            record.metadata_json = metadata_json
        db.flush()
        return record

    def delete(self, db: Session, document_id: str) -> bool:
        record = self.get_by_document_id(db, document_id)
        if record is None:
            return False
        db.delete(record)
        db.flush()
        return True
