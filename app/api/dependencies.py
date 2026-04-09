from __future__ import annotations

from typing import cast

from fastapi import Request

from app.core.config import Settings
from app.services.container import ServiceContainer


def get_settings(request: Request) -> Settings:
    return cast(Settings, request.app.state.settings)


def get_services(request: Request) -> ServiceContainer:
    return cast(ServiceContainer, request.app.state.services)
