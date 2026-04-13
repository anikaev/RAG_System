from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class KnowledgeDocumentCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=256)
    content: str = Field(min_length=1, max_length=100_000)
    subject: str = Field(default="informatics", min_length=1, max_length=64)
    topic: str | None = Field(default=None, max_length=128)
    task_id: str | None = Field(default=None, max_length=128)
    source_type: str = Field(default="manual", min_length=1, max_length=32)
    source_uri: str | None = Field(default=None, max_length=512)
    original_filename: str | None = Field(default=None, max_length=256)
    metadata_json: dict[str, str] = Field(default_factory=dict)


class KnowledgeDocumentSummaryData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    document_id: str
    title: str
    source_type: str
    source_uri: str | None = None
    original_filename: str | None = None
    subject: str
    topic: str | None = None
    task_id: str | None = None
    status: str
    chunk_count: int = Field(ge=0)
    created_at: datetime | None = None
    updated_at: datetime | None = None


class KnowledgeDocumentDetailData(KnowledgeDocumentSummaryData):
    content_raw: str
    metadata_json: dict[str, str] = Field(default_factory=dict)


class KnowledgeDocumentListData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    documents: list[KnowledgeDocumentSummaryData] = Field(default_factory=list)
    total: int = Field(ge=0)


class KnowledgeDocumentDeleteResponseData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    document_id: str
    deleted: bool
