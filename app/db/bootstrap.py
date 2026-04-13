from __future__ import annotations

import logging
from pathlib import Path

from app.db.session import DatabaseSessionManager
from app.kb.loaders import load_seed_documents
from app.providers.interfaces import EmbeddingProvider
from app.services.knowledge_ingestion_service import KnowledgeIngestionService

logger = logging.getLogger(__name__)


def seed_knowledge_chunks(
    db_manager: DatabaseSessionManager,
    seed_path: Path,
    *,
    embedding_provider: EmbeddingProvider | None = None,
    chunk_size_chars: int = 320,
    overlap_paragraphs: int = 1,
) -> int:
    if embedding_provider is None:
        raise ValueError("seed_knowledge_chunks requires an embedding provider.")

    ingestion_service = KnowledgeIngestionService(
        db_manager=db_manager,
        embedding_provider=embedding_provider,
        chunk_size_chars=chunk_size_chars,
        overlap_paragraphs=overlap_paragraphs,
    )
    imported = 0
    for document in load_seed_documents(seed_path):
        record = ingestion_service.ingest_loaded_document(
            document,
            title=document.metadata.get("title", document.source_id),
            source_type="seed",
            source_uri=document.source_id,
            original_filename=document.source_id,
            document_id=f"seed:{document.source_id.rsplit('.', 1)[0]}",
            content_raw=document.content,
        )
        imported += record.chunk_count

    logger.info("db.seeded_knowledge_chunks imported=%s path=%s", imported, seed_path)
    return imported
