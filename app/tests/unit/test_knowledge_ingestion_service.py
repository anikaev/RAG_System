from __future__ import annotations

from app.core.config import Settings
from app.db.repositories import KnowledgeChunkRepository, KnowledgeDocumentRepository
from app.db.session import DatabaseSessionManager
from app.providers.mock_embedding_provider import MockEmbeddingProvider
from app.services.knowledge_ingestion_service import KnowledgeIngestionService


def test_knowledge_ingestion_service_persists_document_and_chunks(tmp_path):
    db_url = f"sqlite+pysqlite:///{tmp_path / 'kb-ingestion.db'}"
    settings = Settings(
        postgres_url=db_url,
        session_backend="database",
        database_bootstrap_schema=True,
        seed_demo_data_on_startup=False,
    )
    db_manager = DatabaseSessionManager(settings)
    db_manager.create_schema()

    service = KnowledgeIngestionService(
        db_manager=db_manager,
        embedding_provider=MockEmbeddingProvider(),
        chunk_size_chars=120,
        overlap_paragraphs=1,
    )

    record = service.ingest_text_document(
        title="Prefix sums intro",
        content=(
            "Префиксные суммы позволяют быстро считать сумму на отрезке.\n\n"
            "Сначала строится массив накопленных сумм.\n\n"
            "Потом ответ на запрос вычисляется через разность двух значений."
        ),
        subject="informatics",
        topic="prefix_sums",
        task_id="prefix-demo",
        metadata_json={"difficulty": "basic"},
    )

    assert record.document_id.startswith("doc-")
    assert record.chunk_count >= 2
    assert record.metadata_json["difficulty"] == "basic"

    document_repository = KnowledgeDocumentRepository()
    chunk_repository = KnowledgeChunkRepository()
    with db_manager.session_scope() as db:
        stored_document = document_repository.get_by_document_id(db, record.document_id)
        stored_chunks = chunk_repository.list_for_document(db, record.document_id)

    assert stored_document is not None
    assert stored_document.title == "Prefix sums intro"
    assert len(stored_chunks) == record.chunk_count
    assert all(chunk.document_id == record.document_id for chunk in stored_chunks)
    assert all(chunk.embedding_json is not None for chunk in stored_chunks)
