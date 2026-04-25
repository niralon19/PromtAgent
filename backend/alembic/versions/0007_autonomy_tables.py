"""Autonomy tables: autonomous_actions, action_tier_config, shadow_mode_decisions

Revision ID: 0007
Revises: 0006
Create Date: 2026-04-25
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "action_tier_config",
        sa.Column("action_key", sa.Text, primary_key=True),
        sa.Column("autonomous_tier", sa.Integer, nullable=False, server_default="0"),
        sa.Column("promoted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("demoted_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "autonomous_actions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "incident_id",
            UUID(as_uuid=True),
            sa.ForeignKey("incidents.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column("action_key", sa.Text, nullable=False, index=True),
        sa.Column("parameters", JSONB, nullable=True),
        sa.Column("success", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("error", sa.Text, nullable=True),
        sa.Column(
            "executed_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )

    op.create_table(
        "shadow_mode_decisions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "incident_id",
            UUID(as_uuid=True),
            sa.ForeignKey("incidents.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column("action_key", sa.Text, nullable=False),
        sa.Column("parameters", JSONB, nullable=True),
        sa.Column("confidence", sa.Integer, nullable=True),
        sa.Column("hypothesis", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )


def downgrade() -> None:
    op.drop_table("shadow_mode_decisions")
    op.drop_table("autonomous_actions")
    op.drop_table("action_tier_config")
