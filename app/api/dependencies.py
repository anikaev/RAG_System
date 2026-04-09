from __future__ import annotations

from fastapi import Request

from app.core.config import Settings
from app.services.container import ServiceContainer


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_services(request: Request) -> ServiceContainer:
    return request.app.state.services
