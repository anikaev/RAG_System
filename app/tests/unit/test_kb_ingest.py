from __future__ import annotations

from pathlib import Path

from app.kb.chunking import chunk_document
from app.kb.ingest import build_ingestion_report, build_seed_chunks
from app.kb.loaders import load_seed_documents
from app.kb.models import LoadedDocument


def test_load_seed_documents_parses_metadata_and_cleans_content():
    seed_path = Path(__file__).resolve().parents[2] / "kb" / "seed"

    documents = load_seed_documents(seed_path)

    assert documents
    assert documents[0].source_id.endswith(".md")
    assert documents[0].subject == "informatics"
    assert documents[0].content


def test_chunk_document_splits_long_content_and_enriches_metadata():
    document = LoadedDocument(
        source_id="demo.md",
        subject="informatics",
        topic="demo-topic",
        task_id="demo-task",
        metadata={"subject": "informatics", "topic": "demo-topic", "task_id": "demo-task"},
        content="\n\n".join(
            [
                "Первый абзац " * 8,
                "Второй абзац " * 8,
                "Третий абзац " * 8,
            ]
        ),
    )

    chunks = chunk_document(document, target_size_chars=120, overlap_paragraphs=1)

    assert len(chunks) >= 2
    assert chunks[0].chunk_id == "demo:0"
    assert chunks[0].metadata_json["chunk_index"] == "0"
    assert chunks[-1].metadata_json["chunk_count"] == str(len(chunks))


def test_build_seed_chunks_and_report_are_consistent():
    seed_path = Path(__file__).resolve().parents[2] / "kb" / "seed"

    chunks = build_seed_chunks(seed_path, target_size_chars=140, overlap_paragraphs=1)
    report = build_ingestion_report(chunks)

    assert chunks
    assert report.document_count == 2
    assert report.chunk_count == len(chunks)
    assert report.chunk_ids[0].endswith(":0")
