from __future__ import annotations

import logging
from time import perf_counter
from contextvars import ContextVar
from typing import Any, cast
from uuid import uuid4

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from app.core.config import Settings
from app.core.metrics import MetricsRegistry

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
        started_at = perf_counter()
        metrics = cast(MetricsRegistry | None, getattr(request.app.state, "metrics", None))

        try:
            logger.info(
                "request.started",
                extra={
                    "event": "request.started",
                    "http_method": request.method,
                    "path": request.url.path,
                },
            )
            response = await call_next(request)
        except Exception:
            latency_ms = (perf_counter() - started_at) * 1000
            if metrics is not None:
                metrics.record_request(status_code=500, latency_ms=latency_ms)
            logger.exception(
                "request.failed",
                extra={
                    "event": "request.failed",
                    "http_method": request.method,
                    "path": request.url.path,
                    "status_code": 500,
                    "latency_ms": round(latency_ms, 3),
                },
            )
            _request_id_ctx.reset(token)
            raise

        response.headers[self.settings.request_id_header] = request_id
        latency_ms = (perf_counter() - started_at) * 1000
        if metrics is not None:
            metrics.record_request(status_code=response.status_code, latency_ms=latency_ms)
        logger.info(
            "request.completed",
            extra={
                "event": "request.completed",
                "http_method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "latency_ms": round(latency_ms, 3),
            },
        )
        _request_id_ctx.reset(token)
        return response
