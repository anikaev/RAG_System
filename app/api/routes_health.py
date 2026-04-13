from __future__ import annotations

from typing import cast

from fastapi import APIRouter, Request

from app.api.dependencies import get_services, get_settings
from app.core.config import Settings
from app.core.metrics import MetricsRegistry
from app.core.request_context import get_request_id
from app.schemas.common import ApiResponse, HealthResponseData, MetricsResponseData, success_response
from app.services.container import ServiceContainer
from app.services.runtime_diagnostics import build_runtime_summary

router = APIRouter(tags=["health"])


@router.get("/health", response_model=ApiResponse[HealthResponseData])
async def healthcheck(request: Request) -> ApiResponse[HealthResponseData]:
    settings = get_settings(request)
    services = get_services(request)
    runtime_summary = build_runtime_summary(settings=settings, services=services)
    return success_response(
        data=HealthResponseData(status="ok", **runtime_summary),
        request_id=get_request_id(request),
    )


@router.get("/metrics", response_model=ApiResponse[MetricsResponseData])
async def metrics(request: Request) -> ApiResponse[MetricsResponseData]:
    registry = cast(MetricsRegistry, request.app.state.metrics)
    snapshot = registry.snapshot()
    return success_response(
        data=MetricsResponseData(
            total_requests=snapshot.total_requests,
            total_errors=snapshot.total_errors,
            avg_latency_ms=snapshot.avg_latency_ms,
            total_code_executions=snapshot.total_code_executions,
            avg_code_execution_ms=snapshot.avg_code_execution_ms,
            runner_status_counts=snapshot.runner_status_counts,
        ),
        request_id=get_request_id(request),
    )
