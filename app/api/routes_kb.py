from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.api.dependencies import get_services
from app.core.request_context import get_request_id
from app.schemas.common import ApiResponse, success_response
from app.schemas.kb import (
    KnowledgeDocumentCreateRequest,
    KnowledgeDocumentDeleteResponseData,
    KnowledgeDocumentDetailData,
    KnowledgeDocumentListData,
    KnowledgeDocumentSummaryData,
)
from app.services.container import ServiceContainer
from app.services.knowledge_ingestion_service import KnowledgeDocumentRecord, KnowledgeIngestionService

router = APIRouter(prefix="/v1/kb", tags=["knowledge-base"])


@router.post(
    "/documents",
    response_model=ApiResponse[KnowledgeDocumentDetailData],
    status_code=status.HTTP_201_CREATED,
)
async def create_document(
    payload: KnowledgeDocumentCreateRequest,
    request: Request,
    services: ServiceContainer = Depends(get_services),
) -> ApiResponse[KnowledgeDocumentDetailData]:
    service = _require_ingestion_service(services)
    record = service.ingest_text_document(
        title=payload.title,
        content=payload.content,
        subject=payload.subject,
        topic=payload.topic,
        task_id=payload.task_id,
        source_type=payload.source_type,
        source_uri=payload.source_uri,
        original_filename=payload.original_filename,
        metadata_json=payload.metadata_json,
    )
    return success_response(
        data=_to_detail_data(record),
        request_id=get_request_id(request),
    )


@router.get("/documents", response_model=ApiResponse[KnowledgeDocumentListData])
async def list_documents(
    request: Request,
    services: ServiceContainer = Depends(get_services),
) -> ApiResponse[KnowledgeDocumentListData]:
    service = _require_ingestion_service(services)
    records = service.list_documents()
    return success_response(
        data=KnowledgeDocumentListData(
            documents=[_to_summary_data(record) for record in records],
            total=len(records),
        ),
        request_id=get_request_id(request),
    )


@router.get("/documents/{document_id}", response_model=ApiResponse[KnowledgeDocumentDetailData])
async def get_document(
    document_id: str,
    request: Request,
    services: ServiceContainer = Depends(get_services),
) -> ApiResponse[KnowledgeDocumentDetailData]:
    service = _require_ingestion_service(services)
    record = service.get_document(document_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Knowledge document not found.")
    return success_response(
        data=_to_detail_data(record),
        request_id=get_request_id(request),
    )


@router.delete(
    "/documents/{document_id}",
    response_model=ApiResponse[KnowledgeDocumentDeleteResponseData],
)
async def delete_document(
    document_id: str,
    request: Request,
    services: ServiceContainer = Depends(get_services),
) -> ApiResponse[KnowledgeDocumentDeleteResponseData]:
    service = _require_ingestion_service(services)
    deleted = service.delete_document(document_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Knowledge document not found.")
    return success_response(
        data=KnowledgeDocumentDeleteResponseData(
            document_id=document_id,
            deleted=True,
        ),
        request_id=get_request_id(request),
    )


def _require_ingestion_service(
    services: ServiceContainer,
) -> KnowledgeIngestionService:
    if services.knowledge_ingestion_service is None:
        raise HTTPException(
            status_code=503,
            detail="Knowledge base management requires database backend.",
        )
    return services.knowledge_ingestion_service


def _to_summary_data(record: KnowledgeDocumentRecord) -> KnowledgeDocumentSummaryData:
    return KnowledgeDocumentSummaryData(
        document_id=record.document_id,
        title=record.title,
        source_type=record.source_type,
        source_uri=record.source_uri,
        original_filename=record.original_filename,
        subject=record.subject,
        topic=record.topic,
        task_id=record.task_id,
        status=record.status,
        chunk_count=record.chunk_count,
    )


def _to_detail_data(record: KnowledgeDocumentRecord) -> KnowledgeDocumentDetailData:
    summary = _to_summary_data(record)
    return KnowledgeDocumentDetailData(
        **summary.model_dump(),
        content_raw=record.content_raw,
        metadata_json=record.metadata_json,
    )
