from __future__ import annotations

import uuid

import structlog
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Incident
from app.services.ikb.embeddings import EmbeddingService

log = structlog.get_logger(__name__)


def build_embedding_text(incident: Incident) -> str:
    """Build a consistent text representation of an incident for embedding.

    The format is fixed so that embeddings are comparable across incidents.
    Including resolution data (if present) makes the embedding richer for retrieval.
    """
    alert = incident.alert
    parts = [
        f"category: {incident.category or 'unknown'}",
        f"hostname: {incident.hostname}",
        f"alertname: {alert.alertname if alert else 'unknown'}",
        f"severity: {alert.severity if alert else 'unknown'}",
    ]

    if alert and alert.annotations:
        summary = alert.annotations.get("summary") or alert.annotations.get("description") or ""
        if summary:
            parts.append(f"description: {summary}")

    # IKB fields (populated after investigation)
    inv = incident.investigation or {}
    if inv.get("hypothesis"):
        parts.append(f"hypothesis: {inv['hypothesis']}")

    # Resolution (populated after ticket resolution — richest signal)
    res = incident.resolution or {}
    if res.get("resolution_category"):
        parts.append(f"resolution: {res['resolution_category']}")
    if res.get("actual_resolution_details"):
        parts.append(f"resolution_details: {res['actual_resolution_details']}")
    if res.get("was_hypothesis_correct"):
        parts.append(f"hypothesis_correct: {res['was_hypothesis_correct']}")

    if incident.tags:
        parts.append(f"tags: {' '.join(incident.tags)}")

    return ". ".join(parts)


class IncidentEmbedder:
    """Computes and persists incident embeddings."""

    def __init__(self, embedding_service: EmbeddingService, db: AsyncSession) -> None:
        self._svc = embedding_service
        self._db = db

    async def embed_and_store(self, incident_id: uuid.UUID) -> None:
        """Compute embedding for a fresh incident and store it."""
        result = await self._db.execute(select(Incident).where(Incident.id == incident_id))
        incident = result.scalar_one_or_none()
        if incident is None:
            log.warning("embed_incident_not_found", incident_id=str(incident_id))
            return

        text = build_embedding_text(incident)
        vector = await self._svc.embed(text)

        await self._db.execute(
            update(Incident).where(Incident.id == incident_id).values(embedding=vector)
        )
        await self._db.flush()
        log.debug("incident_embedded", incident_id=str(incident_id), text_length=len(text))

    async def re_embed_resolved(self, incident_id: uuid.UUID) -> None:
        """Re-compute embedding after resolution data is added (richer signal)."""
        await self.embed_and_store(incident_id)
        log.info("incident_re_embedded_post_resolution", incident_id=str(incident_id))
