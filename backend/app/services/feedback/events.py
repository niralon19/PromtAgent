"""Redis pubsub event emitter for feedback events."""
from __future__ import annotations

import json
import uuid
from typing import Any

import structlog

log = structlog.get_logger(__name__)


async def emit_feedback_event(
    redis_client: Any,
    event_type: str,
    incident_id: uuid.UUID,
    payload: dict,
) -> None:
    """Publish a feedback event to Redis pub/sub channel."""
    if redis_client is None:
        return
    try:
        message = json.dumps({
            "event": event_type,
            "incident_id": str(incident_id),
            **payload,
        })
        await redis_client.publish(f"feedback:{event_type}", message)
    except Exception as exc:
        log.warning("feedback_event_emit_failed", event=event_type, error=str(exc))
