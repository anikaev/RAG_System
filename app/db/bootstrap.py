from __future__ import annotations

import logging
from collections.abc import Sequence
from pathlib import Path

from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from app.db.repositories import KnowledgeChunkRepository
from app.db.session import DatabaseSessionManager
from app.kb.ingest import build_seed_chunks
from app.providers.interfaces import EmbeddingProvider

logger = logging.getLogger(__name__)


def seed_knowledge_chunks(
    db_manager: DatabaseSessionManager,
    seed_path: Path,
    *,
    embedding_provider: EmbeddingProvider | None = None,
    chunk_size_chars: int = 320,
    overlap_paragraphs: int = 1,
) -> int:
    repository = KnowledgeChunkRepository()
    prepared_chunks = build_seed_chunks(
        seed_path,
        target_size_chars=chunk_size_chars,
        overlap_paragraphs=overlap_paragraphs,
    )
    imported = 0
    embeddings: Sequence[list[float] | None]
    if embedding_provider is not None and prepared_chunks:
        embeddings = embedding_provider.embed([chunk.content for chunk in prepared_chunks])
    else:
        embeddings = [None] * len(prepared_chunks)

    with db_manager.session_scope() as db:
        pgvector_ready = _has_pgvector_column(db)
        for chunk, embedding in zip(prepared_chunks, embeddings, strict=True):
            repository.upsert(
                db,
                chunk_id=chunk.chunk_id,
                source_id=chunk.source_id,
                subject=chunk.subject,
                topic=chunk.topic,
                task_id=chunk.task_id,
                content=chunk.content,
                metadata_json=chunk.metadata_json,
                embedding_json=embedding,
            )
            if pgvector_ready and embedding is not None:
                _sync_pgvector_embedding(db, chunk.chunk_id, embedding)
            imported += 1

    logger.info("db.seeded_knowledge_chunks imported=%s path=%s", imported, seed_path)
    return imported


def _has_pgvector_column(db: Session) -> bool:
    bind = db.get_bind()
    if bind is None or bind.dialect.name != "postgresql":
        return False
    columns = inspect(bind).get_columns("knowledge_chunks")
    return any(column["name"] == "embedding_vector" for column in columns)


def _sync_pgvector_embedding(db: Session, chunk_id: str, embedding: list[float]) -> None:
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
