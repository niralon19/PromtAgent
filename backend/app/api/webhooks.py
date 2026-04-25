from __future__ import annotations

import uuid
from typing import Annotated

import structlog
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db
from app.db import models
from app.schemas.alert import GrafanaWebhookPayload
from app.schemas.incident import WebhookResponse
from app.services.triage.pipeline import TriagePipeline

router = APIRouter(prefix="/webhooks", tags=["webhooks"])
log = structlog.get_logger(__name__)

# Module-level pipeline instance (stateless, safe to reuse)
_triage_pipeline = TriagePipeline()


def _extract_hostname(labels: dict[str, str]) -> str:
    for key in ("hostname", "host", "instance", "server"):
        if key in labels:
            return labels[key].split(":")[0]
    return "unknown"


def _extract_severity(labels: dict[str, str], annotations: dict[str, str]) -> str:
    return labels.get("severity") or annotations.get("severity") or "warning"


def _extract_value(values: dict[str, float] | None) -> float | None:
    if not values:
        return None
    return next(iter(values.values()), None)


async def _run_triage(alert_id: uuid.UUID, incident_id: uuid.UUID) -> None:
    """Background task: runs triage pipeline on a persisted alert+incident pair."""
    from app.db.session import AsyncSessionLocal
    from app.db.models import Alert, Incident
    from sqlalchemy import select

    async with AsyncSessionLocal() as db:
        try:
            alert_result = await db.execute(select(Alert).where(Alert.id == alert_id))
            alert = alert_result.scalar_one_or_none()
            incident_result = await db.execute(select(Incident).where(Incident.id == incident_id))
            incident = incident_result.scalar_one_or_none()

            if alert is None or incident is None:
                log.error("triage_background_missing_records", alert_id=str(alert_id), incident_id=str(incident_id))
                return

            result = await _triage_pipeline.run(alert, incident, db)
            await db.commit()
            log.info(
                "triage_background_completed",
                action=result.action,
                incident_id=str(result.incident_id),
                category=result.category,
            )
        except Exception as exc:
            await db.rollback()
            log.error("triage_background_failed", incident_id=str(incident_id), error=str(exc), exc_info=True)


@router.post(
    "/grafana",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=WebhookResponse,
)
async def receive_grafana_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> WebhookResponse:
    """Receive and persist a Grafana unified alerting webhook.

    Saves alert+incident immediately, then runs triage asynchronously
    so the 202 response is returned without delay.

    Raises:
        HTTPException 400: Invalid JSON body.
        HTTPException 422: Invalid Grafana payload schema.
    """
    bound_log = log.bind(endpoint="receive_grafana_webhook")

    try:
        raw_body = await request.json()
    except Exception as exc:
        bound_log.warning("invalid_json_body", error=str(exc))
        raise HTTPException(status_code=400, detail="Invalid JSON body") from exc

    try:
        payload = GrafanaWebhookPayload.model_validate(raw_body)
    except Exception as exc:
        bound_log.warning("invalid_webhook_payload", error=str(exc))
        raise HTTPException(
            status_code=422, detail=f"Invalid Grafana webhook payload: {exc}"
        ) from exc

    bound_log = bound_log.bind(alert_count=len(payload.alerts), status=payload.status)
    bound_log.info("grafana_webhook_received")

    incident_ids: list[str] = []

    for alert_data in payload.alerts:
        if alert_data.status != "firing":
            bound_log.debug("skipping_non_firing_alert", fingerprint=alert_data.fingerprint)
            continue

        labels = dict(alert_data.labels)
        annotations = dict(alert_data.annotations)
        hostname = _extract_hostname(labels)
        severity = _extract_severity(labels, annotations)
        value = _extract_value(alert_data.values)
        alertname = labels.get("alertname", "unknown")

        alert_record = models.Alert(
            id=uuid.uuid4(),
            grafana_fingerprint=alert_data.fingerprint,
            status=alert_data.status,
            alertname=alertname,
            hostname=hostname,
            severity=severity,
            value=value,
            labels=labels,
            annotations=annotations,
            raw_payload=raw_body,
        )
        db.add(alert_record)
        await db.flush()

        incident = models.Incident(
            id=uuid.uuid4(),
            fingerprint=alert_data.fingerprint,  # refined by triage pipeline
            category=labels.get("category"),
            hostname=hostname,
            status="triaging",
            alert_id=alert_record.id,
        )
        db.add(incident)
        await db.flush()

        background_tasks.add_task(_run_triage, alert_record.id, incident.id)

        bound_log.info(
            "incident_queued_for_triage",
            incident_id=str(incident.id),
            alert_id=str(alert_record.id),
            hostname=hostname,
            alertname=alertname,
        )
        incident_ids.append(str(incident.id))

    return WebhookResponse(received=len(incident_ids), incident_ids=incident_ids)


@router.post("/jira", status_code=status.HTTP_200_OK, tags=["webhooks"])
async def receive_jira_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
) -> dict:
    """Receive Jira issue-updated webhooks (resolution sync).

    Jira must be configured to POST to this endpoint on issue transitions.
    """
    try:
        payload = await request.json()
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid JSON") from exc

    issue = payload.get("issue", {})
    issue_key = issue.get("key")
    event_type = payload.get("webhookEvent", "")

    if not issue_key:
        return {"status": "ignored", "reason": "no issue key"}

    bound_log = log.bind(issue_key=issue_key, event_type=event_type)

    if event_type in ("jira:issue_updated", "jira:issue_resolved"):
        fields = issue.get("fields", {})
        transition_status = fields.get("status", {}).get("name", "")

        if transition_status.lower() in ("resolved", "done", "closed"):
            background_tasks.add_task(_handle_jira_resolution, issue_key, fields)
            bound_log.info("jira_resolution_queued")
            return {"status": "queued"}

    bound_log.debug("jira_webhook_ignored")
    return {"status": "ignored"}


async def _handle_jira_resolution(issue_key: str, fields: dict) -> None:
    """Background: process a Jira ticket resolution."""
    try:
        from app.services.jira.sync_handler import JiraSyncHandler
        from app.db.session import AsyncSessionLocal
        async with AsyncSessionLocal() as db:
            handler = JiraSyncHandler(db)
            await handler.handle_resolution(issue_key, fields)
            await db.commit()
    except Exception as exc:
        log.error("jira_resolution_handler_failed", issue_key=issue_key, error=str(exc), exc_info=True)
