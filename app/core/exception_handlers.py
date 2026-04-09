from __future__ import annotations

import logging
from typing import Any, cast

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.request_context import get_request_id
from app.schemas.common import error_response

logger = logging.getLogger(__name__)


def _json_error(
    request: Request,
    *,
    status_code: int,
    code: str,
    message: str,
    details: Any = None,
) -> JSONResponse:
    payload = error_response(
        request_id=get_request_id(request),
        code=code,
        message=message,
        details=details,
    )
    return JSONResponse(status_code=status_code, content=payload.model_dump(mode="json"))


def register_exception_handlers(application: FastAPI) -> None:
    @application.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        return _json_error(
            request,
            status_code=422,
            code="validation_error",
            message="Request validation failed.",
            details=exc.errors(),
        )

    @application.exception_handler(HTTPException)
    async def handle_http_exception(
        request: Request,
        exc: HTTPException,
    ) -> JSONResponse:
        raw_detail = cast(Any, exc.detail)
        detail = raw_detail if isinstance(raw_detail, (dict, list)) else None
        message = raw_detail if isinstance(raw_detail, str) else "Request failed."
        return _json_error(
            request,
            status_code=exc.status_code,
            code="http_error",
            message=message,
            details=detail,
        )

    @application.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("unexpected_error", exc_info=exc)
        return _json_error(
            request,
            status_code=500,
            code="internal_error",
            message="Internal server error.",
        )
