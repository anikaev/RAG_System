from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

ResponseDataT = TypeVar("ResponseDataT")


class ApiError(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    message: str
    details: Any = None


class ResponseMeta(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request_id: str
    version: str = "v1"
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ApiResponse(BaseModel, Generic[ResponseDataT]):
    model_config = ConfigDict(extra="forbid")

    ok: bool
    data: ResponseDataT | None = None
    error: ApiError | None = None
    meta: ResponseMeta


class HealthResponseData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str = "ok"
    session_backend: str | None = None
    retriever_backend: str | None = None
    retriever_ready: bool | None = None
    retriever_status: str | None = None
    embedding_provider: str | None = None
    llm_provider: str | None = None
    code_execution_backend: str | None = None
    configured_session_backend: str | None = None
    configured_retriever_backend: str | None = None
    configured_embedding_provider: str | None = None


class MetricsResponseData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    total_requests: int
    total_errors: int
    avg_latency_ms: float
    total_code_executions: int
    avg_code_execution_ms: float
    runner_status_counts: dict[str, int] = Field(default_factory=dict)


def success_response(data: ResponseDataT, request_id: str) -> ApiResponse[ResponseDataT]:
    return ApiResponse[ResponseDataT](
        ok=True,
        data=data,
        error=None,
        meta=ResponseMeta(request_id=request_id),
    )


def error_response(
    *,
    request_id: str,
    code: str,
    message: str,
    details: Any = None,
) -> ApiResponse[None]:
    return ApiResponse[None](
        ok=False,
        data=None,
        error=ApiError(code=code, message=message, details=details),
        meta=ResponseMeta(request_id=request_id),
    )
