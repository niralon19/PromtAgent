from __future__ import annotations

import structlog
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models import Incident
from app.services.jira.client import JiraClient
from app.services.jira.templates import build_ticket_content

log = structlog.get_logger(__name__)


class TicketCreator:
    """Creates Jira tickets from investigation results."""

    def __init__(self, client: JiraClient | None = None) -> None:
        self._client = client or JiraClient()

    async def create_from_investigation(
        self,
        incident: Incident,
        investigation: dict | None = None,
        enrichment: dict | None = None,
        db: AsyncSession | None = None,
    ) -> dict:
        """Create a Jira ticket and store the reference on the incident.

        Args:
            incident: The Incident ORM object.
            investigation: Serialized InvestigationResult (optional).
            enrichment: Serialized EnrichmentContext (optional).
            db: AsyncSession for updating the incident (optional).

        Returns:
            Jira issue dict with at least {"key": "NOC-123", "id": "..."}.
        """
        bound_log = log.bind(incident_id=str(incident.id), hostname=incident.hostname)

        # Check for existing ticket on parent (avoid spam)
        if incident.parent_incident_id and incident.ticket:
            bound_log.info("ticket_exists_on_parent_adding_comment")
            parent_key = (incident.ticket or {}).get("key")
            if parent_key:
                comment_body = {
                    "version": 1,
                    "type": "doc",
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [{"type": "text", "text": f"Child incident {incident.id} also affected: {incident.hostname}"}],
                        }
                    ],
                }
                await self._client.add_comment(parent_key, comment_body)
                return {"key": parent_key, "reused": True}

        incident_data = {
            "id": str(incident.id),
            "hostname": incident.hostname,
            "category": incident.category,
            "alert": {
                "alertname": incident.alert.alertname if incident.alert else "unknown",
                "severity": incident.alert.severity if incident.alert else "warning",
            } if hasattr(incident, "alert") and incident.alert else {},
        }

        content = build_ticket_content(incident_data, investigation, enrichment)

        project_key = settings.jira_project_key or "NOC"
        issue_type = getattr(settings, "jira_issue_type", "Task")

        fields: dict = {
            "project": {"key": project_key},
            "issuetype": {"name": issue_type},
            "summary": content.summary,
            "description": content.description_adf,
            **content.custom_fields,
        }

        try:
            issue = await self._client.create_issue(fields)
            ticket_ref = {"key": issue.get("key"), "id": issue.get("id"), "url": issue.get("self")}

            if db is not None:
                await db.execute(
                    update(Incident).where(Incident.id == incident.id).values(ticket=ticket_ref)
                )
                await db.flush()

            bound_log.info("ticket_created", key=ticket_ref["key"])
            return ticket_ref

        except Exception as exc:
            bound_log.error("ticket_creation_failed", error=str(exc))
            if db is not None:
                await db.execute(
                    update(Incident)
                    .where(Incident.id == incident.id)
                    .values(ticket={"pending": True, "error": str(exc)})
                )
                await db.flush()
            raise
