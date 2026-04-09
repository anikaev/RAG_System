from __future__ import annotations

import logging
from collections.abc import Sequence
from pathlib import Path

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
            imported += 1

    logger.info("db.seeded_knowledge_chunks imported=%s path=%s", imported, seed_path)
    return imported
