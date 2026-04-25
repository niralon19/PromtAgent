"""initial schema - alerts and incidents tables

Revision ID: 0001
Revises:
Create Date: 2026-04-19

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "alerts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("grafana_fingerprint", sa.String(255), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("alertname", sa.String(255), nullable=False),
        sa.Column("hostname", sa.String(255), nullable=False),
        sa.Column("severity", sa.String(32), nullable=False),
        sa.Column("value", sa.Float(), nullable=True),
        sa.Column("labels", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("annotations", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("raw_payload", postgresql.JSONB(), nullable=False),
        sa.Column(
            "received_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_alerts_grafana_fingerprint", "alerts", ["grafana_fingerprint"])
    op.create_index("ix_alerts_hostname", "alerts", ["hostname"])

    op.create_table(
        "incidents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("fingerprint", sa.String(255), nullable=False),
        sa.Column("category", sa.String(32), nullable=True),
        sa.Column("hostname", sa.String(255), nullable=False),
        sa.Column(
            "status", sa.String(32), nullable=False, server_default="triaging"
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "alert_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("alerts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("correlation", postgresql.JSONB(), nullable=True),
        sa.Column("enrichment", postgresql.JSONB(), nullable=True),
        sa.Column("tool_executions", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("investigation", postgresql.JSONB(), nullable=True),
        sa.Column("ticket", postgresql.JSONB(), nullable=True),
        sa.Column("resolution", postgresql.JSONB(), nullable=True),
        sa.Column("recurrence_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("tags", postgresql.JSONB(), nullable=False, server_default="[]"),
    )
    op.create_index("ix_incidents_fingerprint", "incidents", ["fingerprint"])
    op.create_index("ix_incidents_hostname", "incidents", ["hostname"])
    op.create_index("ix_incidents_status", "incidents", ["status"])
    op.create_index("ix_incidents_status_created", "incidents", ["status", "created_at"])
    op.create_index("ix_incidents_hostname_status", "incidents", ["hostname", "status"])


def downgrade() -> None:
    op.drop_table("incidents")
    op.drop_table("alerts")
