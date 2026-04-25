"""ShadowExecutor — record what the agent WOULD have done without acting."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

log = structlog.get_logger(__name__)


class ShadowExecutor:
    """Record autonomous decisions without executing them."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def record(
        self,
        incident_id: uuid.UUID,
        action_key: str,
        parameters: dict,
        confidence: int,
        hypothesis: str,
    ) -> None:
        """Persist a shadow-mode decision for later review."""
        try:
            import json
            await self._db.execute(
                text("""
                    INSERT INTO shadow_mode_decisions
                        (id, incident_id, action_key, parameters, confidence, hypothesis, created_at)
                    VALUES (:id, :incident_id, :action_key, :params::jsonb, :conf, :hyp, :now)
                """).bindparams(
                    id=uuid.uuid4(),
                    incident_id=incident_id,
                    action_key=action_key,
                    params=json.dumps(parameters),
                    conf=confidence,
                    hyp=hypothesis,
                    now=datetime.now(timezone.utc),
                )
            )
            log.info("shadow_decision_recorded", action=action_key, incident_id=str(incident_id))
        except Exception as exc:
            log.error("shadow_record_failed", error=str(exc))
