"""simulation player run tables

Revision ID: 0004_simulation_player_runs
Revises: 0003_seed_the_haunting_adventure
Create Date: 2026-07-02
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0004_simulation_player_runs"
down_revision = "0003_seed_the_haunting_adventure"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "simulation_runs",
        sa.Column("id", sa.String(length=128), primary_key=True),
        sa.Column("session_id", sa.String(length=96), sa.ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("actor_id", sa.String(length=96), nullable=False),
        sa.Column("persona", postgresql.JSONB(), nullable=False),
        sa.Column("config", postgresql.JSONB(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("report", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("trace_id", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_simulation_runs_session", "simulation_runs", ["session_id", "created_at"])

    op.create_table(
        "simulation_turns",
        sa.Column("id", sa.String(length=128), primary_key=True),
        sa.Column("run_id", sa.String(length=128), sa.ForeignKey("simulation_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("turn_index", sa.Integer(), nullable=False),
        sa.Column("player_action", sa.Text(), nullable=False),
        sa.Column("player_notes", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("gm_result", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("committed_events", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("completion", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("trace_id", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_simulation_turns_run", "simulation_turns", ["run_id", "turn_index"])


def downgrade() -> None:
    op.drop_index("ix_simulation_turns_run", table_name="simulation_turns")
    op.drop_table("simulation_turns")
    op.drop_index("ix_simulation_runs_session", table_name="simulation_runs")
    op.drop_table("simulation_runs")
