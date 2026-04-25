"""Re-embed resolved incidents to capture resolution knowledge."""
from __future__ import annotations

import uuid

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Incident
from app.services.ikb.incident_embedder import IncidentEmbedder

log = structlog.get_logger(__name__)


async def re_embed_resolved_incident(
    db: AsyncSession,
    incident_id: uuid.UUID,
    embedding_service=None,
) -> None:
    """Re-compute and store embedding after resolution data is available."""
    try:
        embedder = IncidentEmbedder(db, embedding_service)
        incident = await db.get(Incident, incident_id)
        if incident is None:
            log.warning("re_embed_incident_not_found", incident_id=str(incident_id))
            return
        await embedder.re_embed_resolved(incident)
        log.info("re_embed_completed", incident_id=str(incident_id))
    except Exception as exc:
        log.error("re_embed_failed", incident_id=str(incident_id), error=str(exc))
