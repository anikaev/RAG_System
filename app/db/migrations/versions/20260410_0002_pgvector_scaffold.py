from __future__ import annotations

from alembic import op

revision = "20260410_0002"
down_revision = "20260409_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute(
        """
        ALTER TABLE knowledge_chunks
        ADD COLUMN IF NOT EXISTS embedding_vector vector(8)
        """
    )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    op.execute(
        """
        ALTER TABLE knowledge_chunks
        DROP COLUMN IF EXISTS embedding_vector
        """
    )
