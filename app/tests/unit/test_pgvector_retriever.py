from __future__ import annotations

from app.core.config import Settings
from app.db.session import DatabaseSessionManager
from app.providers.mock_embedding_provider import MockEmbeddingProvider
from app.providers.pgvector_retriever import PgvectorRetrieverBackend


def test_pgvector_retriever_reports_not_ready_on_sqlite(tmp_path):
    settings = Settings(
        postgres_url=f"sqlite+pysqlite:///{tmp_path / 'pgvector-scaffold.db'}",
        seed_demo_data_on_startup=False,
    )
    db_manager = DatabaseSessionManager(settings)
    db_manager.create_schema()
    backend = PgvectorRetrieverBackend(
        db_manager=db_manager,
        embedding_provider=MockEmbeddingProvider(),
        settings=settings,
    )

    ready, reason = backend.is_ready()

    assert ready is False
    assert reason is not None
    assert "postgresql" in reason.lower()
