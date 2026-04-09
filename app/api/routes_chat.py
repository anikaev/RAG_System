from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from app.api.dependencies import get_services
from app.core.request_context import get_request_id
from app.schemas.chat import ChatRequest, ChatResponseData
from app.schemas.common import ApiResponse, success_response
from app.services.container import ServiceContainer

router = APIRouter(prefix="/v1/chat", tags=["chat"])


@router.post("/respond", response_model=ApiResponse[ChatResponseData])
async def respond(
    payload: ChatRequest,
    request: Request,
    services: ServiceContainer = Depends(get_services),
) -> ApiResponse[ChatResponseData]:
    response = services.chat_service.respond(payload)
    return success_response(data=response, request_id=get_request_id(request))
