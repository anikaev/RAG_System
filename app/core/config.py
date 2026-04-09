from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="RAG_",
        extra="ignore",
    )

    app_name: str = "RAG Tutor API"
    app_env: str = "local"
    log_level: str = "INFO"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    request_id_header: str = "X-Request-ID"
    api_prefix: str = "/v1"

    postgres_url: str = "postgresql+psycopg://rag:rag@localhost:5432/rag"
    redis_url: str = "redis://localhost:6379/0"
    session_backend: Literal["auto", "memory", "database"] = "memory"
    database_fallback_to_memory: bool = True
    database_bootstrap_schema: bool = False
    database_echo: bool = False
    seed_demo_data_on_startup: bool = True
    llm_provider_mode: Literal["mock"] = "mock"
    embedding_provider_mode: Literal["mock"] = "mock"
    retriever_backend_mode: Literal["fallback", "pgvector"] = "fallback"
    retriever_fallback_to_lexical: bool = True
    code_execution_backend_mode: Literal["stub"] = "stub"

    runner_timeout_seconds: int = 2
    runner_cpu_limit: float = 0.5
    runner_memory_mb: int = 128

    max_chat_message_length: int = 4000
    max_code_length: int = 12000
    kb_seed_path: Path = Field(default=PROJECT_ROOT / "app" / "kb" / "seed")
    kb_chunk_size_chars: int = 320
    kb_chunk_overlap_paragraphs: int = 1
    pgvector_dimensions: int = 8

    blocked_code_patterns: tuple[str, ...] = (
        "import os",
        "import subprocess",
        "from subprocess",
        "socket.",
        "requests.",
        "httpx.",
        "eval(",
        "exec(",
        "open(",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
