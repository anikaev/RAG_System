from __future__ import annotations

from fastapi import FastAPI

from app.api.router import api_router
from app.core.config import Settings, get_settings
from app.core.exception_handlers import register_exception_handlers
from app.core.logging import configure_logging
from app.core.metrics import MetricsRegistry
from app.core.request_context import RequestContextMiddleware
from app.services.container import build_service_container


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved_settings = settings or get_settings()
    configure_logging(resolved_settings.log_level)

    application = FastAPI(
        title=resolved_settings.app_name,
        version="0.1.0",
        docs_url="/docs",
        openapi_url="/openapi.json",
    )
    metrics_registry = MetricsRegistry()
    application.state.settings = resolved_settings
    application.state.metrics = metrics_registry
    application.state.services = build_service_container(
        resolved_settings,
        metrics_registry=metrics_registry,
    )
    application.add_middleware(RequestContextMiddleware, settings=resolved_settings)
    application.include_router(api_router)
    register_exception_handlers(application)
    return application


app = create_app()
