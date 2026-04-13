from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from app.db.models import KnowledgeDocument
from app.db.repositories import KnowledgeChunkRepository, KnowledgeDocumentRepository
from app.db.session import DatabaseSessionManager
from app.kb.chunking import chunk_document
from app.kb.cleaners import clean_document_text
from app.kb.models import LoadedDocument
from app.providers.interfaces import EmbeddingProvider


@dataclass(frozen=True, slots=True)
class KnowledgeDocumentRecord:
    document_id: str
    title: str
    source_type: str
    source_uri: str | None
    original_filename: str | None
    subject: str
    topic: str | None
    task_id: str | None
    status: str
    content_raw: str
    metadata_json: dict[str, str]
    chunk_count: int


class KnowledgeIngestionService:
    def __init__(
        self,
        *,
        db_manager: DatabaseSessionManager,
        embedding_provider: EmbeddingProvider,
        chunk_size_chars: int = 320,
        overlap_paragraphs: int = 1,
    ) -> None:
        self.db_manager = db_manager
        self.embedding_provider = embedding_provider
        self.chunk_size_chars = chunk_size_chars
        self.overlap_paragraphs = overlap_paragraphs
        self.document_repository = KnowledgeDocumentRepository()
        self.chunk_repository = KnowledgeChunkRepository()

    def ingest_text_document(
        self,
        *,
        title: str,
        content: str,
        subject: str,
        topic: str | None = None,
        task_id: str | None = None,
        source_type: str = "manual",
        source_uri: str | None = None,
        original_filename: str | None = None,
        metadata_json: dict[str, str] | None = None,
        document_id: str | None = None,
    ) -> KnowledgeDocumentRecord:
        cleaned_content = clean_document_text(content)
        if not cleaned_content:
            raise ValueError("Document content is empty after normalization.")

        resolved_document_id = document_id or self._generate_document_id()
        metadata = {str(key): str(value) for key, value in (metadata_json or {}).items()}
        metadata.setdefault("document_id", resolved_document_id)
        metadata.setdefault("title", title)
        metadata.setdefault("source_type", source_type)

        document = LoadedDocument(
            source_id=resolved_document_id,
            subject=subject,
            topic=topic,
            task_id=task_id,
            metadata=metadata,
            content=cleaned_content,
        )
        return self.ingest_loaded_document(
            document,
            title=title,
            source_type=source_type,
            source_uri=source_uri,
            original_filename=original_filename,
            document_id=resolved_document_id,
            content_raw=content.strip(),
        )

    def ingest_loaded_document(
        self,
        document: LoadedDocument,
        *,
        title: str,
        source_type: str,
        source_uri: str | None = None,
        original_filename: str | None = None,
        document_id: str | None = None,
        content_raw: str | None = None,
    ) -> KnowledgeDocumentRecord:
        resolved_document_id = document_id or self._document_id_for_seed(document.source_id)
        metadata = {str(key): str(value) for key, value in document.metadata.items()}
        metadata.setdefault("document_id", resolved_document_id)
        metadata.setdefault("title", title)
        metadata.setdefault("source_type", source_type)

        normalized_document = LoadedDocument(
            source_id=document.source_id,
            subject=document.subject,
            topic=document.topic,
            task_id=document.task_id,
            metadata=metadata,
            content=document.content,
        )
        prepared_chunks = chunk_document(
            normalized_document,
            target_size_chars=self.chunk_size_chars,
            overlap_paragraphs=self.overlap_paragraphs,
        )
        embeddings = (
            self.embedding_provider.embed(
                [chunk.content for chunk in prepared_chunks],
                input_type="document",
            )
            if prepared_chunks
            else []
        )

        with self.db_manager.session_scope() as db:
            self.document_repository.upsert(
                db,
                document_id=resolved_document_id,
                title=title,
                source_type=source_type,
                source_uri=source_uri,
                original_filename=original_filename,
                subject=normalized_document.subject,
                topic=normalized_document.topic,
                task_id=normalized_document.task_id,
                status="ready",
                content_raw=(content_raw or normalized_document.content).strip(),
                metadata_json=metadata,
            )
            self.chunk_repository.delete_for_document(db, resolved_document_id)
            pgvector_ready = self._has_pgvector_column(db)
            for chunk, embedding in zip(prepared_chunks, embeddings, strict=True):
                chunk_metadata = dict(chunk.metadata_json)
                chunk_metadata["document_id"] = resolved_document_id
                self.chunk_repository.upsert(
                    db,
                    chunk_id=chunk.chunk_id,
                    document_id=resolved_document_id,
                    source_id=chunk.source_id,
                    subject=chunk.subject,
                    topic=chunk.topic,
                    task_id=chunk.task_id,
                    content=chunk.content,
                    metadata_json=chunk_metadata,
                    embedding_json=embedding,
                )
                if pgvector_ready and embedding is not None:
                    self._sync_pgvector_embedding(db, chunk.chunk_id, embedding)

        record = self.get_document(resolved_document_id)
        if record is None:
            raise RuntimeError("Document was not persisted correctly.")
        return record

    def list_documents(self) -> list[KnowledgeDocumentRecord]:
        with self.db_manager.session_scope() as db:
            rows = self.document_repository.list_with_chunk_counts(db)
            return [
                self._to_record(document, chunk_count)
                for document, chunk_count in rows
            ]

    def get_document(self, document_id: str) -> KnowledgeDocumentRecord | None:
        with self.db_manager.session_scope() as db:
            document = self.document_repository.get_by_document_id(db, document_id)
            if document is None:
                return None
            chunk_count = self.chunk_repository.count_for_document(db, document_id)
            return self._to_record(document, chunk_count)

    def delete_document(self, document_id: str) -> bool:
        with self.db_manager.session_scope() as db:
            self.chunk_repository.delete_for_document(db, document_id)
            return self.document_repository.delete(db, document_id)

    @staticmethod
    def _generate_document_id() -> str:
        return f"doc-{uuid4().hex[:12]}"

    @staticmethod
    def _document_id_for_seed(source_id: str) -> str:
        return f"seed:{source_id.rsplit('.', 1)[0]}"

    @staticmethod
    def _to_record(
        document: KnowledgeDocument,
        chunk_count: int,
    ) -> KnowledgeDocumentRecord:
        return KnowledgeDocumentRecord(
            document_id=document.document_id,
            title=document.title,
            source_type=document.source_type,
            source_uri=document.source_uri,
            original_filename=document.original_filename,
            subject=document.subject,
            topic=document.topic,
            task_id=document.task_id,
            status=document.status,
            content_raw=document.content_raw,
            metadata_json={
                str(key): str(value)
                for key, value in document.metadata_json.items()
            }
            if isinstance(document.metadata_json, dict)
            else {},
            chunk_count=chunk_count,
        )

    @staticmethod
    def _has_pgvector_column(db: Session) -> bool:
        bind = db.get_bind()
        if bind is None or bind.dialect.name != "postgresql":
            return False
        columns = inspect(bind).get_columns("knowledge_chunks")
        return any(column["name"] == "embedding_vector" for column in columns)

    @staticmethod
    def _sync_pgvector_embedding(
        db: Session,
        chunk_id: str,
        embedding: list[float],
    ) -> None:
        db.execute(
            text(
                """
                UPDATE knowledge_chunks
                SET embedding_vector = CAST(:embedding AS vector)
                WHERE chunk_id = :chunk_id
                """
            ),
            {
                "embedding": "[" + ",".join(f"{value:.6f}" for value in embedding) + "]",
                "chunk_id": chunk_id,
            },
        )
