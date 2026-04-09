from __future__ import annotations

from pathlib import Path

from app.kb.cleaners import clean_document_text
from app.kb.models import LoadedDocument


def load_seed_documents(seed_path: Path) -> list[LoadedDocument]:
    documents: list[LoadedDocument] = []
    for path in sorted(seed_path.glob("*.md")):
        metadata, content = parse_seed_document(path.read_text(encoding="utf-8"))
        cleaned_content = clean_document_text(content)
        if not cleaned_content:
            continue

        enriched_metadata = dict(metadata)
        enriched_metadata.setdefault("source_id", path.name)
        enriched_metadata.setdefault("subject", "informatics")

        documents.append(
            LoadedDocument(
                source_id=path.name,
                subject=enriched_metadata["subject"],
                topic=enriched_metadata.get("topic"),
                task_id=enriched_metadata.get("task_id"),
                metadata=enriched_metadata,
                content=cleaned_content,
            )
        )
    return documents


def parse_seed_document(raw_text: str) -> tuple[dict[str, str], str]:
    metadata: dict[str, str] = {}
    lines = raw_text.splitlines()
    content_start = 0

    for index, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            content_start = index + 1
            break
        if ":" not in stripped:
            break
        key, value = stripped.split(":", 1)
        metadata[key.strip()] = value.strip()
        content_start = index + 1

    content = "\n".join(lines[content_start:])
    return metadata, content
