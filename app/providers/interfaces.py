from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field


class RetrievedContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    chunk_id: str
    content: str
    score: float = Field(ge=0.0)
    metadata: dict[str, str] = Field(default_factory=dict)


class LLMGenerationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_message: str
    mode: str
    hint_level: int = Field(ge=0, le=4)
    refusal: bool = False
    context: list[RetrievedContext] = Field(default_factory=list)
    hint_level_description: str | None = None
    response_template: str | None = None


class LLMGenerationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    response_text: str
    guiding_question: str | None = None
    confidence: float = Field(ge=0.0, le=1.0)
    metadata: dict[str, Any] = Field(default_factory=dict)


class CodeExecutionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    language: str
    code: str
    task_id: str | None = None


class CodeExecutionResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str
    public_tests_passed: int = 0
    public_tests_total: int = 0
    hidden_tests_summary: str = "not_run"
    runner_available: bool = False
    details: dict[str, Any] = Field(default_factory=dict)


@runtime_checkable
class LLMProvider(Protocol):
    def generate(self, request: LLMGenerationRequest) -> LLMGenerationResult:
        ...


@runtime_checkable
class EmbeddingProvider(Protocol):
    def embed(self, texts: list[str]) -> list[list[float]]:
        ...


@runtime_checkable
class RetrieverBackend(Protocol):
    def search(
        self,
        query: str,
        *,
        subject: str | None = None,
        topic: str | None = None,
        task_id: str | None = None,
        top_k: int = 3,
    ) -> list[RetrievedContext]:
        ...


@runtime_checkable
class CodeExecutionBackend(Protocol):
    def execute(self, request: CodeExecutionRequest) -> CodeExecutionResult:
        ...
