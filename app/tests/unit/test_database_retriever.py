from __future__ import annotations

from sqlalchemy import delete

from app.core.config import Settings
from app.db.bootstrap import seed_knowledge_chunks
from app.db.models import KnowledgeChunk
from app.db.session import DatabaseSessionManager
from app.providers.database_retriever import DatabaseLexicalRetriever
from app.providers.mock_embedding_provider import MockEmbeddingProvider
from app.providers.retrieval_cache import MemoryRetrievalCache


def test_database_retriever_returns_relevant_seed_chunk(tmp_path):
    db_url = f"sqlite+pysqlite:///{tmp_path / 'retriever.db'}"
    settings = Settings(
        postgres_url=db_url,
        session_backend="database",
        database_bootstrap_schema=True,
        seed_demo_data_on_startup=False,
    )
    db_manager = DatabaseSessionManager(settings)
    db_manager.create_schema()
    seed_knowledge_chunks(
        db_manager,
        settings.kb_seed_path,
        embedding_provider=MockEmbeddingProvider(),
        chunk_size_chars=settings.kb_chunk_size_chars,
        overlap_paragraphs=settings.kb_chunk_overlap_paragraphs,
    )

    retriever = DatabaseLexicalRetriever(db_manager)

    results = retriever.search("Как устроен цикл for в Python", subject="informatics")

    assert results
    assert results[0].metadata["topic"] == "python_loops"
    assert retriever.is_ready() is True


def test_database_retriever_uses_cache_when_rows_change(tmp_path):
    db_url = f"sqlite+pysqlite:///{tmp_path / 'retriever_cache.db'}"
    settings = Settings(
        postgres_url=db_url,
        session_backend="database",
        database_bootstrap_schema=True,
        seed_demo_data_on_startup=False,
    )
    db_manager = DatabaseSessionManager(settings)
    db_manager.create_schema()
    seed_knowledge_chunks(
        db_manager,
        settings.kb_seed_path,
        embedding_provider=MockEmbeddingProvider(),
        chunk_size_chars=settings.kb_chunk_size_chars,
        overlap_paragraphs=settings.kb_chunk_overlap_paragraphs,
    )

    retriever = DatabaseLexicalRetriever(
        db_manager,
        cache_backend=MemoryRetrievalCache(),
    )

    initial = retriever.search("Как устроен цикл for в Python", subject="informatics")
    assert initial

    with db_manager.session_scope() as db:
        db.execute(delete(KnowledgeChunk))

    cached = retriever.search("Как устроен цикл for в Python", subject="informatics")

    assert cached
    assert cached[0].chunk_id == initial[0].chunk_id
