from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class GrafanaAlertData(BaseModel):
    """Single alert within a Grafana unified alerting webhook payload."""

    status: str
    labels: dict[str, str] = Field(default_factory=dict)
    annotations: dict[str, str] = Field(default_factory=dict)
    startsAt: datetime
    endsAt: datetime | None = None
    generatorURL: str = ""
    fingerprint: str
    values: dict[str, float] | None = None
    silenceURL: str = ""
    dashboardURL: str = ""
    panelURL: str = ""


class GrafanaWebhookPayload(BaseModel):
    """Grafana unified alerting webhook payload (Grafana 8+)."""

    receiver: str
    status: str
    alerts: list[GrafanaAlertData]
    groupLabels: dict[str, str] = Field(default_factory=dict)
    commonLabels: dict[str, str] = Field(default_factory=dict)
    commonAnnotations: dict[str, str] = Field(default_factory=dict)
    externalURL: str = ""
    version: str = "1"
    groupKey: str = ""
    truncatedAlerts: int = 0
    title: str = ""
    state: str = ""
    message: str = ""


class AlertResponse(BaseModel):
    id: str
    grafana_fingerprint: str
    status: str
    alertname: str
    hostname: str
    severity: str
    received_at: datetime

    model_config = {"from_attributes": True}
