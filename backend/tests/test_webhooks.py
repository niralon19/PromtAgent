from __future__ import annotations

from uuid import UUID

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Alert, Incident

FIRING_PAYLOAD = {
    "receiver": "noc-receiver",
    "status": "firing",
    "alerts": [
        {
            "status": "firing",
            "labels": {
                "alertname": "HighCPU",
                "hostname": "server-01",
                "severity": "critical",
                "category": "physical",
            },
            "annotations": {
                "summary": "CPU usage is high",
                "description": "CPU at 95%",
            },
            "startsAt": "2024-01-01T10:00:00Z",
            "endsAt": "0001-01-01T00:00:00Z",
            "generatorURL": "http://grafana.local/graph",
            "fingerprint": "test-fp-abc123",
            "values": {"A": 95.0},
        }
    ],
    "groupLabels": {"alertname": "HighCPU"},
    "commonLabels": {"hostname": "server-01"},
    "commonAnnotations": {},
    "externalURL": "http://grafana.local",
    "version": "1",
    "groupKey": '{}:{alertname="HighCPU"}',
}


async def test_webhook_returns_202(client: AsyncClient) -> None:
    response = await client.post("/api/v1/webhooks/grafana", json=FIRING_PAYLOAD)
    assert response.status_code == 202


async def test_webhook_creates_incident(client: AsyncClient, db_session: AsyncSession) -> None:
    response = await client.post("/api/v1/webhooks/grafana", json=FIRING_PAYLOAD)
    assert response.status_code == 202

    data = response.json()
    assert data["received"] == 1
    assert len(data["incident_ids"]) == 1

    incident_id = UUID(data["incident_ids"][0])
    result = await db_session.execute(select(Incident).where(Incident.id == incident_id))
    incident = result.scalar_one_or_none()

    assert incident is not None
    assert incident.hostname == "server-01"
    assert incident.status == "triaging"
    assert incident.category == "physical"


async def test_webhook_saves_alert(client: AsyncClient, db_session: AsyncSession) -> None:
    response = await client.post("/api/v1/webhooks/grafana", json=FIRING_PAYLOAD)
    assert response.status_code == 202

    data = response.json()
    incident_id = UUID(data["incident_ids"][0])

    result = await db_session.execute(select(Incident).where(Incident.id == incident_id))
    incident = result.scalar_one()

    alert_result = await db_session.execute(
        select(Alert).where(Alert.id == incident.alert_id)
    )
    alert = alert_result.scalar_one()

    assert alert.alertname == "HighCPU"
    assert alert.hostname == "server-01"
    assert alert.severity == "critical"
    assert alert.value == 95.0
    assert alert.grafana_fingerprint == "test-fp-abc123"


async def test_webhook_invalid_payload_returns_422(client: AsyncClient) -> None:
    response = await client.post("/api/v1/webhooks/grafana", json={"invalid": "payload"})
    assert response.status_code == 422


async def test_webhook_resolved_alert_not_counted(client: AsyncClient) -> None:
    resolved_payload = {
        **FIRING_PAYLOAD,
        "alerts": [{**FIRING_PAYLOAD["alerts"][0], "status": "resolved"}],
    }
    response = await client.post("/api/v1/webhooks/grafana", json=resolved_payload)
    assert response.status_code == 202
    assert response.json()["received"] == 0


async def test_webhook_multiple_firing_alerts(client: AsyncClient) -> None:
    multi_payload = {
        **FIRING_PAYLOAD,
        "alerts": [
            {**FIRING_PAYLOAD["alerts"][0], "fingerprint": "fp-001", "labels": {
                **FIRING_PAYLOAD["alerts"][0]["labels"], "hostname": "server-02"
            }},
            {**FIRING_PAYLOAD["alerts"][0], "fingerprint": "fp-002", "labels": {
                **FIRING_PAYLOAD["alerts"][0]["labels"], "hostname": "server-03"
            }},
        ],
    }
    response = await client.post("/api/v1/webhooks/grafana", json=multi_payload)
    assert response.status_code == 202
    assert response.json()["received"] == 2
    assert len(response.json()["incident_ids"]) == 2


async def test_health_endpoint(client: AsyncClient) -> None:
    response = await client.get("/health")
    assert response.status_code in (200, 503)
    data = response.json()
    assert "status" in data
    assert "database" in data
