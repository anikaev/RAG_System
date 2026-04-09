from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class LoadedDocument:
    source_id: str
    subject: str
    topic: str | None
    task_id: str | None
    metadata: dict[str, str]
    content: str


@dataclass(slots=True)
class PreparedKnowledgeChunk:
    chunk_id: str
    source_id: str
    subject: str
    topic: str | None
    task_id: str | None
    content: str
    metadata_json: dict[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class IngestionReport:
    document_count: int
    chunk_count: int
    source_ids: list[str]
    chunk_ids: list[str]
