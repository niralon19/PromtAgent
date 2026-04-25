from __future__ import annotations

from datetime import datetime, timezone

import structlog
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Incident

log = structlog.get_logger(__name__)

_RESOLUTION_FIELDS = ("resolution_category", "was_hypothesis_correct", "actual_resolution_details")


class JiraSyncHandler:
    """Processes Jira resolution webhooks and updates the DB incident."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def handle_resolution(self, issue_key: str, fields: dict) -> None:
        """Update incident from Jira resolution fields.

        Args:
            issue_key: Jira issue key (e.g. NOC-42).
            fields: Jira issue fields dict from the webhook payload.
        """
        bound_log = log.bind(issue_key=issue_key)

        # Find incident by ticket key
        result = await self._db.execute(select(Incident).where(
            Incident.ticket["key"].as_string() == issue_key
        ))
        incident = result.scalar_one_or_none()

        if incident is None:
            bound_log.warning("sync_handler_incident_not_found")
            return

        if incident.resolution and incident.resolution.get("resolved_at"):
            bound_log.info("sync_handler_already_resolved")
            return  # idempotent

        bound_log = bound_log.bind(incident_id=str(incident.id))

        # Extract custom resolution fields (field IDs vary by Jira instance)
        from app.core.config import settings
        field_ids: dict = getattr(settings, "jira_custom_field_ids", {}) or {}

        resolution_category = (
            _get_field(fields, field_ids.get("resolution_category", "customfield_resolution_category"))
            or _get_select_name(fields, "resolution")
        )
        was_hypothesis_correct = _get_field(
            fields, field_ids.get("was_hypothesis_correct", "customfield_was_hypothesis_correct")
        )
        actual_resolution_details = _get_field(
            fields, field_ids.get("actual_resolution_details", "customfield_actual_resolution_details")
        )

        resolution_time_minutes: int | None = None
        if incident.created_at:
            delta = datetime.now(timezone.utc) - incident.created_at
            resolution_time_minutes = int(delta.total_seconds() / 60)

        resolution_data = {
            "resolution_category": resolution_category,
            "was_hypothesis_correct": was_hypothesis_correct,
            "actual_resolution_details": actual_resolution_details,
            "resolution_time_minutes": resolution_time_minutes,
            "resolved_at": datetime.now(timezone.utc).isoformat(),
            "source": "jira_webhook",
        }

        await self._db.execute(
            update(Incident)
            .where(Incident.id == incident.id)
            .values(
                status="resolved",
                resolved_at=datetime.now(timezone.utc),
                resolution=resolution_data,
            )
        )
        await self._db.flush()

        bound_log.info(
            "incident_resolved_from_jira",
            resolution_category=resolution_category,
            correct=was_hypothesis_correct,
            duration_minutes=resolution_time_minutes,
        )

        # Trigger feedback loop
        try:
            from app.services.feedback.orchestrator import FeedbackOrchestrator
            orchestrator = FeedbackOrchestrator(self._db)
            await orchestrator.process_resolution(
                incident.id,
                {
                    "resolution_category": resolution_category,
                    "resolution_details": actual_resolution_details,
                    "was_hypothesis_correct": was_hypothesis_correct,
                    "resolution_time_minutes": resolution_time_minutes,
                    "source": "jira_webhook",
                },
            )
        except Exception as exc:
            bound_log.error("feedback_trigger_failed", error=str(exc))


def _get_field(fields: dict, key: str) -> str | None:
    val = fields.get(key)
    if val is None:
        return None
    if isinstance(val, dict):
        return val.get("value") or val.get("name")
    return str(val)


def _get_select_name(fields: dict, key: str) -> str | None:
    val = fields.get(key)
    if isinstance(val, dict):
        return val.get("name")
    return None
