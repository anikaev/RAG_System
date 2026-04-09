from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from app.api.dependencies import get_services
from app.core.request_context import get_request_id
from app.schemas.code import CodeCheckRequest, CodeCheckResponseData
from app.schemas.common import ApiResponse, success_response
from app.services.container import ServiceContainer

router = APIRouter(prefix="/v1/code", tags=["code"])


@router.post("/check", response_model=ApiResponse[CodeCheckResponseData])
async def check_code(
    payload: CodeCheckRequest,
    request: Request,
    services: ServiceContainer = Depends(get_services),
) -> ApiResponse[CodeCheckResponseData]:
    response = services.code_service.check_code(payload)
    return success_response(data=response, request_id=get_request_id(request))
