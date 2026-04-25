"""jira fields - ticket_pending status support

Revision ID: 0003
Revises: 0002
Create Date: 2026-04-19

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ticket JSONB field already exists from migration 0001.
    # This migration is a no-op schema-wise; it documents the Jira stage boundary.
    # Future: add processed_resolution_events table (added in Stage 07).
    pass


def downgrade() -> None:
    pass
