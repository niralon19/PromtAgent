"""IKB schema - pgvector embedding, metric baselines, resolution categories

Revision ID: 0004
Revises: 0003
Create Date: 2026-04-19

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_EMBEDDING_DIM = 384  # sentence-transformers all-MiniLM-L6-v2


def upgrade() -> None:
    # Enable pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # Add IKB columns to incidents table
    op.add_column(
        "incidents",
        sa.Column(
            "embedding",
            sa.Text(),  # stored as text; cast to vector in queries
            nullable=True,
            comment="Serialized float array for pgvector similarity search",
        ),
    )
    op.add_column("incidents", sa.Column("hypothesis", sa.Text(), nullable=True))
    op.add_column("incidents", sa.Column("confidence", sa.SmallInteger(), nullable=True))
    op.add_column("incidents", sa.Column("suggested_action_key", sa.Text(), nullable=True))

    # metric_baselines table
    op.create_table(
        "metric_baselines",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("hostname", sa.String(255), nullable=False),
        sa.Column("metric_name", sa.String(255), nullable=False),
        sa.Column("mean", sa.Float(), nullable=False),
        sa.Column("stddev", sa.Float(), nullable=False),
        sa.Column("p50", sa.Float(), nullable=False),
        sa.Column("p95", sa.Float(), nullable=False),
        sa.Column("p99", sa.Float(), nullable=False),
        sa.Column("sample_count", sa.Integer(), nullable=False),
        sa.Column("window_days", sa.Integer(), nullable=False),
        sa.Column("computed_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("hostname", "metric_name", "window_days", name="uq_metric_baselines"),
    )
    op.create_index("ix_metric_baselines_hostname", "metric_baselines", ["hostname"])

    # resolution_categories seed table
    op.create_table(
        "resolution_categories",
        sa.Column("name", sa.String(64), primary_key=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("category", sa.String(32), nullable=False),
    )

    op.execute("""
        INSERT INTO resolution_categories (name, description, category) VALUES
        ('hardware_replacement', 'A hardware component was replaced', 'physical'),
        ('config_change', 'A configuration change resolved the issue', 'physical'),
        ('restart_service', 'Restarting a service resolved the issue', 'physical'),
        ('cache_clear', 'Clearing a cache resolved the issue', 'physical'),
        ('scheduled_maintenance', 'The incident was part of planned maintenance', 'general'),
        ('false_positive', 'No real issue; alert was a false positive', 'general'),
        ('upstream_issue', 'Root cause was in an upstream system', 'general'),
        ('requires_investigation', 'Issue not resolved; requires deeper investigation', 'general'),
        ('environmental', 'Environmental issue (power, cooling)', 'physical'),
        ('network_peer', 'Issue was caused by a network peer', 'coupling'),
        ('software_bug', 'Software bug identified', 'general'),
        ('capacity', 'Capacity limit reached (disk full, OOM)', 'physical'),
        ('etl_restart', 'ETL pipeline restart resolved data freshness issue', 'data_integrity'),
        ('pipeline_fix', 'Data pipeline fix resolved integrity issue', 'data_integrity'),
        ('bgp_reconvergence', 'BGP protocol re-converged naturally', 'coupling')
    """)

    # Alter embedding column to proper vector type
    op.execute(f"ALTER TABLE incidents ALTER COLUMN embedding TYPE vector({_EMBEDDING_DIM}) USING embedding::vector({_EMBEDDING_DIM})")

    # HNSW index for fast ANN search (requires pgvector 0.5+)
    op.execute(
        "CREATE INDEX ix_incidents_embedding_hnsw ON incidents "
        "USING hnsw (embedding vector_cosine_ops)"
        " WITH (m = 16, ef_construction = 64)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_incidents_embedding_hnsw")
    op.drop_table("resolution_categories")
    op.drop_table("metric_baselines")
    op.drop_column("incidents", "suggested_action_key")
    op.drop_column("incidents", "confidence")
    op.drop_column("incidents", "hypothesis")
    op.drop_column("incidents", "embedding")
