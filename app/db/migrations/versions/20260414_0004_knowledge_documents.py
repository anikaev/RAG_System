from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260414_0004"
down_revision = "20260413_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "knowledge_documents",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("document_id", sa.String(length=128), nullable=False),
        sa.Column("title", sa.String(length=256), nullable=False),
        sa.Column("source_type", sa.String(length=32), nullable=False),
        sa.Column("source_uri", sa.String(length=512), nullable=True),
        sa.Column("original_filename", sa.String(length=256), nullable=True),
        sa.Column("subject", sa.String(length=64), nullable=False),
        sa.Column("topic", sa.String(length=128), nullable=True),
        sa.Column("task_id", sa.String(length=128), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="ready"),
        sa.Column("content_raw", sa.Text(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_knowledge_documents")),
        sa.UniqueConstraint("document_id", name=op.f("uq_knowledge_documents_document_id")),
    )
    op.create_index(
        op.f("ix_knowledge_documents_document_id"),
        "knowledge_documents",
        ["document_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_knowledge_documents_source_type"),
        "knowledge_documents",
        ["source_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_knowledge_documents_status"),
        "knowledge_documents",
        ["status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_knowledge_documents_subject"),
        "knowledge_documents",
        ["subject"],
        unique=False,
    )
    op.create_index(
        op.f("ix_knowledge_documents_task_id"),
        "knowledge_documents",
        ["task_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_knowledge_documents_topic"),
        "knowledge_documents",
        ["topic"],
        unique=False,
    )

    with op.batch_alter_table("knowledge_chunks") as batch_op:
        batch_op.add_column(sa.Column("document_id", sa.String(length=128), nullable=True))
        batch_op.create_index(
            op.f("ix_knowledge_chunks_document_id"),
            ["document_id"],
            unique=False,
        )
        batch_op.create_foreign_key(
            op.f("fk_knowledge_chunks_document_id_knowledge_documents"),
            "knowledge_documents",
            ["document_id"],
            ["document_id"],
            ondelete="CASCADE",
        )

    bind = op.get_bind()
    rows = bind.execute(
        sa.text(
            """
            SELECT source_id, subject, topic, task_id, MIN(content) AS sample_content
            FROM knowledge_chunks
            GROUP BY source_id, subject, topic, task_id
            ORDER BY source_id
            """
        )
    ).mappings()

    for row in rows:
        source_id = str(row["source_id"])
        document_id = f"seed:{source_id.rsplit('.', 1)[0]}"
        bind.execute(
            sa.text(
                """
                INSERT INTO knowledge_documents (
                    document_id,
                    title,
                    source_type,
                    source_uri,
                    original_filename,
                    subject,
                    topic,
                    task_id,
                    status,
                    content_raw,
                    metadata_json,
                    created_at,
                    updated_at
                ) VALUES (
                    :document_id,
                    :title,
                    'seed',
                    :source_uri,
                    :original_filename,
                    :subject,
                    :topic,
                    :task_id,
                    'ready',
                    :content_raw,
                    :metadata_json,
                    CURRENT_TIMESTAMP,
                    CURRENT_TIMESTAMP
                )
                """
            ),
            {
                "document_id": document_id,
                "title": source_id,
                "source_uri": source_id,
                "original_filename": source_id,
                "subject": row["subject"],
                "topic": row["topic"],
                "task_id": row["task_id"],
                "content_raw": row["sample_content"] or "",
                "metadata_json": "{}",
            },
        )
        bind.execute(
            sa.text(
                """
                UPDATE knowledge_chunks
                SET document_id = :document_id
                WHERE source_id = :source_id
                """
            ),
            {
                "document_id": document_id,
                "source_id": source_id,
            },
        )


def downgrade() -> None:
    with op.batch_alter_table("knowledge_chunks") as batch_op:
        batch_op.drop_constraint(
            op.f("fk_knowledge_chunks_document_id_knowledge_documents"),
            type_="foreignkey",
        )
        batch_op.drop_index(op.f("ix_knowledge_chunks_document_id"))
        batch_op.drop_column("document_id")

    op.drop_index(op.f("ix_knowledge_documents_topic"), table_name="knowledge_documents")
    op.drop_index(op.f("ix_knowledge_documents_task_id"), table_name="knowledge_documents")
    op.drop_index(op.f("ix_knowledge_documents_subject"), table_name="knowledge_documents")
    op.drop_index(op.f("ix_knowledge_documents_status"), table_name="knowledge_documents")
    op.drop_index(op.f("ix_knowledge_documents_source_type"), table_name="knowledge_documents")
    op.drop_index(op.f("ix_knowledge_documents_document_id"), table_name="knowledge_documents")
    op.drop_table("knowledge_documents")
