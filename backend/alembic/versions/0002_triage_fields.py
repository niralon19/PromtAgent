"""triage fields - parent_incident_id on incidents

Revision ID: 0002
Revises: 0001
Create Date: 2026-04-19

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "incidents",
        sa.Column(
            "parent_incident_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("incidents.id"),
            nullable=True,
        ),
    )
    op.create_index("ix_incidents_parent_id", "incidents", ["parent_incident_id"])


def downgrade() -> None:
    op.drop_index("ix_incidents_parent_id", "incidents")
    op.drop_column("incidents", "parent_incident_id")
