from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class IncidentResponse(BaseModel):
    id: UUID
    fingerprint: str
    category: str | None
    hostname: str
    status: str
    created_at: datetime
    resolved_at: datetime | None

    model_config = {"from_attributes": True}


class WebhookResponse(BaseModel):
    received: int
    incident_ids: list[str]
