"""Incidents REST API."""
from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db
from app.db.models import Incident

router = APIRouter(prefix="/api/v1/incidents", tags=["incidents"])


def _serialize(incident: Incident) -> dict[str, Any]:
    return {
        "id": str(incident.id),
        "hostname": incident.hostname,
        "category": incident.category,
        "status": incident.status,
        "fingerprint": incident.fingerprint,
        "parent_incident_id": str(incident.parent_incident_id) if incident.parent_incident_id else None,
        "hypothesis": incident.hypothesis,
        "confidence": incident.confidence,
        "suggested_action_key": incident.suggested_action_key,
        "resolution_category": getattr(incident, "resolution_category", None),
        "resolution_details": getattr(incident, "resolution_details", None),
        "was_hypothesis_correct": getattr(incident, "was_hypothesis_correct", None),
        "resolution_time_minutes": getattr(incident, "resolution_time_minutes", None),
        "enrichment": incident.enrichment,
        "investigation": incident.investigation,
        "created_at": incident.created_at.isoformat() if incident.created_at else None,
        "updated_at": incident.updated_at.isoformat() if incident.updated_at else None,
        "alert": {
            "id": str(incident.alert.id),
            "alertname": incident.alert.alertname,
            "severity": incident.alert.severity,
            "value": incident.alert.value,
            "annotations": dict(incident.alert.annotations or {}),
            "labels": dict(incident.alert.labels or {}),
            "status": incident.alert.status,
            "starts_at": incident.alert.starts_at.isoformat() if incident.alert.starts_at else None,
            "fingerprint": incident.alert.fingerprint,
        } if incident.alert else None,
    }


@router.get("")
async def list_incidents(
    status: str | None = Query(None),
    category: str | None = Query(None),
    hostname: str | None = Query(None),
    severity: str | None = Query(None),
    limit: int = Query(100, le=500),
    offset: int = Query(0),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    from sqlalchemy.orm import selectinload
    q = select(Incident).options(selectinload(Incident.alert)).order_by(Incident.created_at.desc())

    if status:
        q = q.where(Incident.status == status)
    if category:
        q = q.where(Incident.category == category)
    if hostname:
        q = q.where(Incident.hostname.ilike(f"%{hostname}%"))
    if severity:
        from app.db.models import Alert
        q = q.join(Alert).where(Alert.severity == severity)

    q = q.limit(limit).offset(offset)
    result = await db.execute(q)
    return [_serialize(i) for i in result.scalars().all()]


@router.get("/{incident_id}")
async def get_incident(incident_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    from sqlalchemy.orm import selectinload
    result = await db.execute(
        select(Incident)
        .options(selectinload(Incident.alert))
        .where(Incident.id == incident_id)
    )
    incident = result.scalar_one_or_none()
    if incident is None:
        raise HTTPException(status_code=404, detail="Incident not found")
    return _serialize(incident)


@router.post("/{incident_id}/acknowledge")
async def acknowledge(incident_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    await _require_incident(incident_id, db)
    await db.execute(update(Incident).where(Incident.id == incident_id).values(status="acknowledged"))
    await db.commit()
    return {"id": str(incident_id), "status": "acknowledged"}


@router.post("/{incident_id}/false-positive")
async def false_positive(incident_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    await _require_incident(incident_id, db)
    await db.execute(update(Incident).where(Incident.id == incident_id).values(status="false_positive"))
    await db.commit()
    return {"id": str(incident_id), "status": "false_positive"}


@router.post("/{incident_id}/escalate")
async def escalate(
    incident_id: uuid.UUID,
    body: dict[str, Any],
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    await _require_incident(incident_id, db)
    await db.execute(
        update(Incident)
        .where(Incident.id == incident_id)
        .values(
            status="open",
            suggested_action_key="ESCALATE_TO_TIER2",
        )
    )
    await db.commit()
    return {"id": str(incident_id), "escalated": True}


@router.get("/{incident_id}/similar")
async def similar_incidents(incident_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> list[dict]:
    from app.services.ikb.similarity import SimilarityService
    svc = SimilarityService(db)
    return [s.model_dump() for s in await svc.find_similar_incidents(incident_id)]


@router.get("/{incident_id}/enrichment")
async def get_enrichment(incident_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> dict:
    result = await db.execute(select(Incident).where(Incident.id == incident_id))
    incident = result.scalar_one_or_none()
    if incident is None:
        raise HTTPException(status_code=404, detail="Incident not found")
    return incident.enrichment or {}


async def _require_incident(incident_id: uuid.UUID, db: AsyncSession) -> None:
    result = await db.execute(select(Incident.id).where(Incident.id == incident_id))
    if result.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="Incident not found")
