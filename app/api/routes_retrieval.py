from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from app.api.dependencies import get_services
from app.core.request_context import get_request_id
from app.schemas.common import ApiResponse, success_response
from app.schemas.retrieval import (
    RetrievalContextData,
    RetrievalDebugRequest,
    RetrievalDebugResponseData,
)
from app.services.container import ServiceContainer
from app.services.runtime_diagnostics import describe_retriever

router = APIRouter(prefix="/v1/retrieval", tags=["retrieval"])


@router.post("/debug", response_model=ApiResponse[RetrievalDebugResponseData])
async def debug_retrieval(
    payload: RetrievalDebugRequest,
    request: Request,
    services: ServiceContainer = Depends(get_services),
) -> ApiResponse[RetrievalDebugResponseData]:
    task_context = payload.task_context
    contexts = services.retriever.search(
        payload.query,
        subject=task_context.subject if task_context else "informatics",
        topic=task_context.topic if task_context else None,
        task_id=task_context.task_id if task_context else None,
        top_k=payload.top_k,
    )
    diagnostics = describe_retriever(services.retriever)
    return success_response(
        data=RetrievalDebugResponseData(
            backend=diagnostics.backend,
            ready=diagnostics.ready,
            status=diagnostics.status,
            query=payload.query,
            context_count=len(contexts),
            contexts=[
                RetrievalContextData(
                    chunk_id=context.chunk_id,
                    content=context.content,
                    score=context.score,
                    metadata=context.metadata,
                )
                for context in contexts
            ],
        ),
        request_id=get_request_id(request),
    )
