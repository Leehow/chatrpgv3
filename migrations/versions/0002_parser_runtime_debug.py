"""parser runtime debug tables

Revision ID: 0002_parser_runtime_debug
Revises: 0001_initial_postgres_schema
Create Date: 2026-07-02
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0002_parser_runtime_debug"
down_revision = "0001_initial_postgres_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "parser_runs",
        sa.Column("id", sa.String(length=128), primary_key=True),
        sa.Column("document_id", sa.String(length=96), nullable=False),
        sa.Column("profile", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("input", postgresql.JSONB(), nullable=False),
        sa.Column("output", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("warnings", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("trace_id", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    op.create_table(
        "llm_calls",
        sa.Column("id", sa.String(length=128), primary_key=True),
        sa.Column("trace_id", sa.String(length=128), nullable=False),
        sa.Column("task", sa.String(length=128), nullable=False),
        sa.Column("model", sa.String(length=128), nullable=False),
        sa.Column("request", postgresql.JSONB(), nullable=False),
        sa.Column("response", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_llm_calls_trace", "llm_calls", ["trace_id", "created_at"])

    op.create_table(
        "source_assets",
        sa.Column("id", sa.String(length=128), primary_key=True),
        sa.Column("document_id", sa.String(length=96), sa.ForeignKey("source_documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("asset_kind", sa.String(length=32), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=False),
        sa.Column("storage_uri", sa.Text(), nullable=False),
        sa.Column("asset_metadata", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )


def downgrade() -> None:
    op.drop_table("source_assets")
    op.drop_index("ix_llm_calls_trace", table_name="llm_calls")
    op.drop_table("llm_calls")
    op.drop_table("parser_runs")
