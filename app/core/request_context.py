from __future__ import annotations

import logging
from contextvars import ContextVar
from typing import Any, cast
from uuid import uuid4

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from app.core.config import Settings

logger = logging.getLogger(__name__)

_request_id_ctx: ContextVar[str | None] = ContextVar("request_id", default=None)


def get_current_request_id() -> str | None:
    return _request_id_ctx.get()


def get_request_id(request: Request | None = None) -> str:
    if request is not None:
        request_id = cast(str | None, getattr(request.state, "request_id", None))
        if request_id:
            return request_id
    return get_current_request_id() or "unknown-request-id"


class RequestContextMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: Any, settings: Settings) -> None:
        super().__init__(app)
        self.settings = settings

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        request_id = request.headers.get(self.settings.request_id_header) or str(uuid4())
        request.state.request_id = request_id
        token = _request_id_ctx.set(request_id)

        logger.info("request.started method=%s path=%s", request.method, request.url.path)
        try:
            response = await call_next(request)
        finally:
            _request_id_ctx.reset(token)

        response.headers[self.settings.request_id_header] = request_id
        logger.info(
            "request.completed method=%s path=%s status=%s",
            request.method,
            request.url.path,
            response.status_code,
        )
        return response
