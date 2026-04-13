from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="RAG_",
        extra="ignore",
        populate_by_name=True,
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
    llm_provider_mode: Literal["mock", "compatible_api"] = "mock"
    embedding_provider_mode: Literal["mock", "jina"] = "mock"
    retriever_backend_mode: Literal["fallback", "pgvector"] = "pgvector"
    retriever_fallback_to_lexical: bool = True
    retrieval_cache_backend_mode: Literal["auto", "disabled", "redis"] = "auto"
    retrieval_cache_ttl_seconds: int = 120
    code_execution_backend_mode: Literal["stub", "docker"] = "stub"
    llm_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("RAG_LLM_API_KEY", "HF_TOKEN"),
    )
    llm_api_base_url: str | None = "http://127.0.0.1:8001/v1"
    llm_model_name: str = "local-model"
    llm_api_timeout_seconds: int = 30
    llm_response_format_mode: Literal["json_object", "json_schema"] = "json_object"
    embedding_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("RAG_EMBEDDING_API_KEY", "JINA_API_KEY"),
    )
    embedding_api_url: str = "https://api.jina.ai/v1/embeddings"
    embedding_model_name: str = "jina-embeddings-v3"
    embedding_api_timeout_seconds: int = 30
    embedding_ssl_verify: bool = True
    embedding_ca_bundle_path: Path | None = None

    runner_timeout_seconds: int = 2
    runner_cpu_limit: float = 0.5
    runner_memory_mb: int = 128
    runner_binary: str = "docker"
    runner_image: str = "rag-python-runner:latest"
    runner_workdir: str = "/workspace"
    runner_tests_path: Path = Field(default=PROJECT_ROOT / "app" / "code_tests")

    max_chat_message_length: int = 4000
    max_code_length: int = 12000
    kb_seed_path: Path = Field(default=PROJECT_ROOT / "app" / "kb" / "seed")
    kb_chunk_size_chars: int = 320
    kb_chunk_overlap_paragraphs: int = 1
    pgvector_dimensions: int = 1024

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
