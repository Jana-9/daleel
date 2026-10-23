"""Create documents, processing jobs and document chunks (with pgvector embeddings).

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-23
"""

from collections.abc import Sequence

import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Frozen here on purpose: a migration must not change if the app's constant changes later.
EMBEDDING_DIM = 384


def _timestamp(name: str) -> sa.Column:
    return sa.Column(name, sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False)


def upgrade() -> None:
    op.create_table(
        "documents",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("storage_key", sa.String(length=255), nullable=False),
        sa.Column("mime_type", sa.String(length=100), nullable=False),
        sa.Column("file_size", sa.BigInteger(), nullable=False),
        sa.Column("page_count", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("error_code", sa.String(length=50), nullable=True),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        _timestamp("created_at"),
        _timestamp("updated_at"),
        sa.CheckConstraint(
            "status IN ('uploaded', 'processing', 'ready', 'failed')", name="ck_documents_status"
        ),
        sa.ForeignKeyConstraint(
            ["owner_id"], ["users.id"], name="fk_documents_owner_id_users", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_documents"),
        sa.UniqueConstraint("storage_key", name="uq_documents_storage_key"),
    )
    op.create_index("ix_documents_owner_id_created_at", "documents", ["owner_id", "created_at"])

    op.create_table(
        "processing_jobs",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("attempts", sa.Integer(), server_default="0", nullable=False),
        sa.Column("error_code", sa.String(length=50), nullable=True),
        sa.Column("error_detail", sa.Text(), nullable=True),
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        _timestamp("created_at"),
        sa.CheckConstraint(
            "status IN ('queued', 'running', 'done', 'failed')", name="ck_processing_jobs_status"
        ),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["documents.id"],
            name="fk_processing_jobs_document_id_documents",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_processing_jobs"),
    )
    op.create_index("ix_processing_jobs_document_id", "processing_jobs", ["document_id"])
    # Workers look for the oldest queued job: this index serves that query.
    op.create_index(
        "ix_processing_jobs_status_created_at", "processing_jobs", ["status", "created_at"]
    )

    op.create_table(
        "document_chunks",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("content_normalized", sa.Text(), nullable=False),
        sa.Column("word_count", sa.Integer(), nullable=False),
        sa.Column("bboxes", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("embedding", Vector(dim=EMBEDDING_DIM), nullable=False),
        sa.Column("embedding_model", sa.String(length=200), nullable=False),
        _timestamp("created_at"),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["documents.id"],
            name="fk_document_chunks_document_id_documents",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_document_chunks"),
        sa.UniqueConstraint(
            "document_id", "chunk_index", name="uq_document_chunks_document_id_index"
        ),
    )
    op.create_index("ix_document_chunks_document_id", "document_chunks", ["document_id"])
    # HNSW: approximate nearest-neighbour index for cosine similarity search.
    op.create_index(
        "ix_document_chunks_embedding_hnsw",
        "document_chunks",
        ["embedding"],
        postgresql_using="hnsw",
        postgresql_with={"m": 16, "ef_construction": 64},
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )


def downgrade() -> None:
    op.drop_table("document_chunks")
    op.drop_table("processing_jobs")
    op.drop_table("documents")
