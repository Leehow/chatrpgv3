"""initial postgres schema

Revision ID: 0001_initial_postgres_schema
Revises:
Create Date: 2026-07-01
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from pgvector.sqlalchemy import Vector

revision = "0001_initial_postgres_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "source_documents",
        sa.Column("id", sa.String(length=96), primary_key=True),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("source_type", sa.String(length=32), nullable=False),
        sa.Column("uri", sa.Text(), nullable=True),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("document_metadata", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    op.create_table(
        "source_blocks",
        sa.Column("id", sa.String(length=128), primary_key=True),
        sa.Column("document_id", sa.String(length=96), sa.ForeignKey("source_documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=False),
        sa.Column("block_index", sa.Integer(), nullable=False),
        sa.Column("block_kind", sa.String(length=32), nullable=False),
        sa.Column("text", sa.Text(), nullable=True),
        sa.Column("bbox", postgresql.JSONB(), nullable=True),
        sa.Column("visibility", sa.String(length=32), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("document_id", "page_number", "block_index", name="uq_source_block_position"),
    )

    op.create_table(
        "rulesets",
        sa.Column("id", sa.String(length=96), primary_key=True),
        sa.Column("system_id", sa.String(length=64), nullable=False),
        sa.Column("edition", sa.String(length=64), nullable=False),
        sa.Column("ir", postgresql.JSONB(), nullable=False),
        sa.Column("source_refs", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("system_id", "edition", name="uq_rulesets_system_edition"),
    )

    op.create_table(
        "adventures",
        sa.Column("id", sa.String(length=96), primary_key=True),
        sa.Column("system_id", sa.String(length=64), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("ir", postgresql.JSONB(), nullable=False),
        sa.Column("source_refs", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    op.create_table(
        "sessions",
        sa.Column("id", sa.String(length=96), primary_key=True),
        sa.Column("system_id", sa.String(length=64), nullable=False),
        sa.Column("adventure_id", sa.String(length=96), nullable=True),
        sa.Column("state", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    op.create_table(
        "domain_events",
        sa.Column("id", sa.String(length=128), primary_key=True),
        sa.Column("session_id", sa.String(length=96), sa.ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("event_type", sa.String(length=96), nullable=False),
        sa.Column("actor_id", sa.String(length=96), nullable=True),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("source_refs", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("trace_id", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_domain_events_session_created", "domain_events", ["session_id", "created_at"])

    op.create_table(
        "semantic_embeddings",
        sa.Column("id", sa.String(length=128), primary_key=True),
        sa.Column("owner_kind", sa.String(length=64), nullable=False),
        sa.Column("owner_id", sa.String(length=128), nullable=False),
        sa.Column("embedding_model", sa.String(length=128), nullable=False),
        sa.Column("embedding", Vector(1536), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index(
        "ix_semantic_embeddings_hnsw",
        "semantic_embeddings",
        ["embedding"],
        postgresql_using="hnsw",
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )

    op.create_table(
        "semantic_matches",
        sa.Column("id", sa.String(length=128), primary_key=True),
        sa.Column("task", sa.String(length=128), nullable=False),
        sa.Column("request", postgresql.JSONB(), nullable=False),
        sa.Column("result", postgresql.JSONB(), nullable=False),
        sa.Column("trace_id", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    op.create_table(
        "trace_spans",
        sa.Column("id", sa.String(length=128), primary_key=True),
        sa.Column("trace_id", sa.String(length=128), nullable=False),
        sa.Column("parent_span_id", sa.String(length=128), nullable=True),
        sa.Column("kind", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_trace_spans_trace", "trace_spans", ["trace_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_trace_spans_trace", table_name="trace_spans")
    op.drop_table("trace_spans")
    op.drop_table("semantic_matches")
    op.drop_index("ix_semantic_embeddings_hnsw", table_name="semantic_embeddings")
    op.drop_table("semantic_embeddings")
    op.drop_index("ix_domain_events_session_created", table_name="domain_events")
    op.drop_table("domain_events")
    op.drop_table("sessions")
    op.drop_table("adventures")
    op.drop_table("rulesets")
    op.drop_table("source_blocks")
    op.drop_table("source_documents")
