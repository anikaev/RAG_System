from __future__ import annotations

from fastapi import APIRouter, Request

from app.core.request_context import get_request_id
from app.schemas.common import ApiResponse, HealthResponseData, success_response

router = APIRouter(tags=["health"])


@router.get("/health", response_model=ApiResponse[HealthResponseData])
async def healthcheck(request: Request) -> ApiResponse[HealthResponseData]:
    return success_response(
        data=HealthResponseData(status="ok"),
        request_id=get_request_id(request),
    )
