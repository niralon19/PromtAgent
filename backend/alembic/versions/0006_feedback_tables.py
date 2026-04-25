"""Feedback loop tables: action_metrics, host_statistics, dashboard_alerts, processed_resolution_events

Revision ID: 0006
Revises: 0005
Create Date: 2026-04-25
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "action_metrics",
        sa.Column("action_key", sa.Text, primary_key=True),
        sa.Column("total_uses", sa.Integer, nullable=False, server_default="0"),
        sa.Column("correct_uses", sa.Integer, nullable=False, server_default="0"),
        sa.Column("avg_resolution_minutes", sa.Numeric(10, 2), nullable=True),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "host_statistics",
        sa.Column("hostname", sa.Text, primary_key=True),
        sa.Column("total_incidents", sa.Integer, nullable=False, server_default="0"),
        sa.Column("open_incidents", sa.Integer, nullable=False, server_default="0"),
        sa.Column("avg_resolution_minutes", sa.Numeric(10, 2), nullable=True),
        sa.Column("most_common_category", sa.Text, nullable=True),
        sa.Column("last_incident_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "dashboard_alerts",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("alert_type", sa.Text, nullable=False),
        sa.Column("title", sa.Text, nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("severity", sa.Text, nullable=False, server_default="'warning'"),
        sa.Column("metadata", JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.UniqueConstraint("alert_type", "title", name="uq_dashboard_alerts_type_title"),
    )

    op.create_table(
        "processed_resolution_events",
        sa.Column(
            "incident_id",
            UUID(as_uuid=True),
            sa.ForeignKey("incidents.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "processed_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )

    # Add resolution fields to incidents (if not added in 0004)
    for col_name, col_type in [
        ("resolution_category", sa.Text),
        ("resolution_details", sa.Text),
        ("resolution_time_minutes", sa.Integer),
    ]:
        try:
            op.add_column("incidents", sa.Column(col_name, col_type, nullable=True))
        except Exception:
            pass  # column may already exist from migration 0004


def downgrade() -> None:
    op.drop_table("processed_resolution_events")
    op.drop_table("dashboard_alerts")
    op.drop_table("host_statistics")
    op.drop_table("action_metrics")
