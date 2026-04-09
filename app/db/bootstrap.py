from __future__ import annotations

import logging
from pathlib import Path

from app.db.repositories import KnowledgeChunkRepository
from app.db.session import DatabaseSessionManager
from app.providers.interfaces import EmbeddingProvider

logger = logging.getLogger(__name__)


def seed_knowledge_chunks(
    db_manager: DatabaseSessionManager,
    seed_path: Path,
    *,
    embedding_provider: EmbeddingProvider | None = None,
) -> int:
    repository = KnowledgeChunkRepository()
    imported = 0

    with db_manager.session_scope() as db:
        for path in sorted(seed_path.glob("*.md")):
            metadata, content = _parse_seed_document(path.read_text(encoding="utf-8"))
            if not content.strip():
                continue
            embedding = None
            if embedding_provider is not None:
                embedding = embedding_provider.embed([content.strip()])[0]

            repository.upsert(
                db,
                chunk_id=f"{path.stem}:0",
                source_id=path.name,
                subject=metadata.get("subject", "informatics"),
                topic=metadata.get("topic"),
                task_id=metadata.get("task_id"),
                content=content.strip(),
                metadata_json=metadata,
                embedding_json=embedding,
            )
            imported += 1

    logger.info("db.seeded_knowledge_chunks imported=%s path=%s", imported, seed_path)
    return imported


def _parse_seed_document(raw_text: str) -> tuple[dict[str, str], str]:
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
