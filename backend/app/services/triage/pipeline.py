from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Literal

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Alert, Incident
from app.services.triage.classifier import ClassificationService
from app.services.triage.correlation import CorrelationService
from app.services.triage.dedup import DedupService
from app.services.triage.fingerprint import compute_fingerprint

log = structlog.get_logger(__name__)


@dataclass
class TriageResult:
    action: Literal["created", "duplicate", "grouped", "manual_review"]
    incident_id: uuid.UUID
    was_duplicate: bool = False
    was_grouped: bool = False
    parent_incident_id: uuid.UUID | None = None
    category: str | None = None
    classification_reason: str = ""


class TriagePipeline:
    """Orchestrates the full triage flow for a single alert."""

    def __init__(
        self,
        dedup: DedupService | None = None,
        correlation: CorrelationService | None = None,
        classifier: ClassificationService | None = None,
        redis_client=None,
    ) -> None:
        self._dedup = dedup or DedupService(redis_client)
        self._correlation = correlation or CorrelationService()
        self._classifier = classifier or ClassificationService()

    async def run(self, alert: Alert, incident: Incident, db: AsyncSession) -> TriageResult:
        """Run the full triage pipeline on a newly-created incident.

        Args:
            alert: The persisted Alert record.
            incident: The freshly-created Incident (status=triaging).
            db: DB session.

        Returns:
            TriageResult describing what happened.
        """
        bound_log = log.bind(
            alert_id=str(alert.id),
            incident_id=str(incident.id),
            hostname=incident.hostname,
        )
        bound_log.info("triage_pipeline_started")

        # 1. Compute fingerprint
        fingerprint = compute_fingerprint(alert.labels or {})
        incident.fingerprint = fingerprint

        # 2. Dedup check
        existing = await self._dedup.check_duplicate(fingerprint, db)
        if existing:
            await self._dedup.increment_recurrence(existing, db)
            await db.flush()
            bound_log.info("triage_duplicate_detected", existing_incident_id=str(existing.id))
            return TriageResult(
                action="duplicate",
                incident_id=existing.id,
                was_duplicate=True,
                category=existing.category,
            )

        # 3. Classify
        category, reason = self._classifier.classify(
            alertname=alert.alertname,
            labels=alert.labels or {},
            annotations=alert.annotations or {},
        )
        incident.category = category if category != "manual_review" else None
        incident.status = "triaging"

        if category == "manual_review":
            bound_log.warning("triage_manual_review", reason=reason)

        # 4. Correlation
        related = await self._correlation.find_related_incidents(incident, db)
        parent = None
        if related:
            parent = await self._correlation.maybe_create_parent(incident, related, db)

        # 5. Register fingerprint for future dedup
        await self._dedup.register(fingerprint, incident.id)
        await db.flush()

        action: Literal["created", "duplicate", "grouped", "manual_review"]
        if parent:
            action = "grouped"
        elif category == "manual_review":
            action = "manual_review"
        else:
            action = "created"

        bound_log.info(
            "triage_pipeline_completed",
            action=action,
            category=category,
            reason=reason,
            has_parent=parent is not None,
        )

        return TriageResult(
            action=action,
            incident_id=incident.id,
            was_grouped=parent is not None,
            parent_incident_id=parent.id if parent else None,
            category=incident.category,
            classification_reason=reason,
        )
