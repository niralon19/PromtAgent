"""FeedbackOrchestrator — process resolution and fan out all feedback steps."""
from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone

import structlog
from sqlalchemy import text, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Incident
from app.services.feedback.action_metrics import record_action_outcome
from app.services.feedback.events import emit_feedback_event
from app.services.feedback.host_statistics import update_host_statistics
from app.services.feedback.re_embedding import re_embed_resolved_incident
from app.services.feedback.recurrence_detector import detect_recurrence

log = structlog.get_logger(__name__)


class FeedbackOrchestrator:
    """Coordinates all feedback steps after an incident is resolved."""

    def __init__(self, db: AsyncSession, redis_client=None, embedding_service=None) -> None:
        self._db = db
        self._redis = redis_client
        self._embedding_service = embedding_service

    async def process_resolution(
        self,
        incident_id: uuid.UUID,
        resolution_data: dict,
    ) -> None:
        """Fan out all feedback steps for a resolved incident.

        resolution_data keys (all optional):
            resolution_category, resolution_details, was_hypothesis_correct,
            resolution_time_minutes, resolved_by, jira_key
        """
        bound_log = log.bind(incident_id=str(incident_id))

        # Idempotency check
        if await self._already_processed(incident_id):
            bound_log.info("feedback_already_processed")
            return

        incident = await self._db.get(Incident, incident_id)
        if incident is None:
            bound_log.warning("feedback_incident_not_found")
            return

        # Persist resolution fields
        resolution_category = resolution_data.get("resolution_category", "unknown")
        was_correct = bool(resolution_data.get("was_hypothesis_correct", False))
        resolution_time = resolution_data.get("resolution_time_minutes")

        await self._db.execute(
            update(Incident)
            .where(Incident.id == incident_id)
            .values(
                status="resolved",
                resolution_category=resolution_category,
                resolution_details=resolution_data.get("resolution_details"),
                was_hypothesis_correct=was_correct,
                resolution_time_minutes=resolution_time,
            )
        )
        await self._db.flush()

        action_key = incident.suggested_action_key or "NOTE_IN_TICKET"
        hostname = incident.hostname or "unknown"
        category = incident.category or "physical"

        # Run all feedback steps concurrently (best-effort)
        results = await asyncio.gather(
            record_action_outcome(self._db, incident_id, action_key, was_correct, resolution_time),
            update_host_statistics(self._db, hostname),
            re_embed_resolved_incident(self._db, incident_id, self._embedding_service),
            detect_recurrence(self._db, incident_id, hostname, category),
            return_exceptions=True,
        )

        recurrence_info = results[3] if not isinstance(results[3], Exception) else {}

        # Mark as processed
        await self._mark_processed(incident_id)

        # Emit event
        await emit_feedback_event(
            self._redis,
            "resolution_processed",
            incident_id,
            {
                "action_key": action_key,
                "was_correct": was_correct,
                "resolution_category": resolution_category,
                "recurrence": recurrence_info,
            },
        )

        bound_log.info(
            "feedback_processing_complete",
            action=action_key,
            correct=was_correct,
            recurrence=recurrence_info.get("is_recurring"),
        )

    async def _already_processed(self, incident_id: uuid.UUID) -> bool:
        try:
            result = await self._db.execute(
                text("SELECT 1 FROM processed_resolution_events WHERE incident_id = :id").bindparams(id=incident_id)
            )
            return result.fetchone() is not None
        except Exception:
            return False

    async def _mark_processed(self, incident_id: uuid.UUID) -> None:
        try:
            await self._db.execute(
                text("""
                    INSERT INTO processed_resolution_events (incident_id, processed_at)
                    VALUES (:id, :now)
                    ON CONFLICT DO NOTHING
                """).bindparams(id=incident_id, now=datetime.now(timezone.utc))
            )
        except Exception as exc:
            log.warning("mark_processed_failed", incident_id=str(incident_id), error=str(exc))
