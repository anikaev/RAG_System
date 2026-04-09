from __future__ import annotations

from pathlib import Path

from app.kb.chunking import chunk_document
from app.kb.loaders import load_seed_documents
from app.kb.models import IngestionReport, PreparedKnowledgeChunk


def build_seed_chunks(
    seed_path: Path,
    *,
    target_size_chars: int = 320,
    overlap_paragraphs: int = 1,
) -> list[PreparedKnowledgeChunk]:
    chunks: list[PreparedKnowledgeChunk] = []
    for document in load_seed_documents(seed_path):
        chunks.extend(
            chunk_document(
                document,
                target_size_chars=target_size_chars,
                overlap_paragraphs=overlap_paragraphs,
            )
        )
    return chunks


def build_ingestion_report(chunks: list[PreparedKnowledgeChunk]) -> IngestionReport:
    source_ids = sorted({chunk.source_id for chunk in chunks})
    chunk_ids = [chunk.chunk_id for chunk in chunks]
    return IngestionReport(
        document_count=len(source_ids),
        chunk_count=len(chunks),
        source_ids=source_ids,
        chunk_ids=chunk_ids,
    )
