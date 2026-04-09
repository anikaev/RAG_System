from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.db.session import DatabaseSessionManager
from app.main import create_app


@pytest.fixture()
def client() -> TestClient:
    settings = Settings(
        session_backend="memory",
        seed_demo_data_on_startup=False,
    )
    with TestClient(create_app(settings)) as test_client:
        yield test_client


@pytest.fixture()
def sqlite_db_url(tmp_path: Path) -> str:
    return f"sqlite+pysqlite:///{tmp_path / 'rag-test.db'}"


@pytest.fixture()
def db_settings(sqlite_db_url: str) -> Settings:
    return Settings(
        postgres_url=sqlite_db_url,
        session_backend="database",
        database_fallback_to_memory=False,
        database_bootstrap_schema=True,
        seed_demo_data_on_startup=True,
    )


@pytest.fixture()
def db_client(db_settings: Settings) -> TestClient:
    with TestClient(create_app(db_settings)) as test_client:
        yield test_client


@pytest.fixture()
def db_manager(db_settings: Settings) -> DatabaseSessionManager:
    manager = DatabaseSessionManager(db_settings)
    manager.create_schema()
    return manager
