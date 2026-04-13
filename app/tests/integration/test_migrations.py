from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect


def test_alembic_upgrade_creates_core_tables(tmp_path: Path):
    db_path = tmp_path / "migration-test.db"
    db_url = f"sqlite+pysqlite:///{db_path}"

    config = Config(str(Path(__file__).resolve().parents[3] / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", db_url)

    command.upgrade(config, "head")

    engine = create_engine(db_url)
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())

    assert {
        "chat_sessions",
        "chat_messages",
        "knowledge_chunks",
        "knowledge_documents",
    } <= tables
