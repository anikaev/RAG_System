from __future__ import annotations

from alembic import op
from sqlalchemy import text

revision = "20260413_0003"
down_revision = "20260410_0002"
branch_labels = None
depends_on = None

TARGET_DIMENSIONS = 1024


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    vector_available = bind.execute(
        text("SELECT 1 FROM pg_available_extensions WHERE name = 'vector' LIMIT 1")
    ).scalar_one_or_none()
    if vector_available is None:
        return

    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute(
        f"""
        ALTER TABLE knowledge_chunks
        ADD COLUMN IF NOT EXISTS embedding_vector vector({TARGET_DIMENSIONS})
        """
    )
    op.execute(
        f"""
        ALTER TABLE knowledge_chunks
        ALTER COLUMN embedding_vector TYPE vector({TARGET_DIMENSIONS})
        USING NULL::vector({TARGET_DIMENSIONS})
        """
    )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    vector_available = bind.execute(
        text("SELECT 1 FROM pg_available_extensions WHERE name = 'vector' LIMIT 1")
    ).scalar_one_or_none()
    if vector_available is None:
        return

    op.execute(
        """
        ALTER TABLE knowledge_chunks
        ALTER COLUMN embedding_vector TYPE vector(8)
        USING NULL::vector(8)
        """
    )
