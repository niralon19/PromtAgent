from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

import sqlalchemy as sa
from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    grafana_fingerprint: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    alertname: Mapped[str] = mapped_column(String(255), nullable=False)
    hostname: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(32), nullable=False)
    value: Mapped[float | None] = mapped_column(Float, nullable=True)
    labels: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    annotations: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    raw_payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    incidents: Mapped[list[Incident]] = relationship("Incident", back_populates="alert")


class Incident(Base):
    __tablename__ = "incidents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    fingerprint: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    category: Mapped[str | None] = mapped_column(String(32), nullable=True)
    hostname: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="triaging", index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    alert_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("alerts.id"), nullable=False
    )
    alert: Mapped[Alert] = relationship("Alert", back_populates="incidents")

    correlation: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    enrichment: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    tool_executions: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    investigation: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    ticket: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    resolution: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    parent_incident_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("incidents.id"), nullable=True, index=True
    )
    children: Mapped[list[Incident]] = relationship(
        "Incident", foreign_keys="Incident.parent_incident_id", back_populates="parent"
    )
    parent: Mapped[Incident | None] = relationship(
        "Incident", foreign_keys="Incident.parent_incident_id", back_populates="children", remote_side="Incident.id"
    )

    recurrence_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    tags: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)

    # IKB fields (populated by enrichment + investigation + resolution)
    hypothesis: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    confidence: Mapped[int | None] = mapped_column(sa.SmallInteger, nullable=True)
    suggested_action_key: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    # embedding stored as text/vector via pgvector — typed as Text in ORM, queried raw
    embedding: Mapped[str | None] = mapped_column(sa.Text, nullable=True)

    __table_args__ = (
        Index("ix_incidents_status_created", "status", "created_at"),
        Index("ix_incidents_hostname_status", "hostname", "status"),
    )
