from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.chat import TaskContext


class RetrievalDebugRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str = Field(min_length=1, max_length=4000)
    task_context: TaskContext | None = None
    top_k: int = Field(default=3, ge=1, le=10)


class RetrievalContextData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    chunk_id: str
    content: str
    score: float = Field(ge=0.0)
    metadata: dict[str, str] = Field(default_factory=dict)


class RetrievalDebugResponseData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    backend: str
    ready: bool | None = None
    status: str | None = None
    query: str
    context_count: int = Field(ge=0)
    contexts: list[RetrievalContextData] = Field(default_factory=list)
