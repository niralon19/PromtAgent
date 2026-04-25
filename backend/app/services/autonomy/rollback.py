"""RollbackService — per-action-type rollback procedures."""
from __future__ import annotations

import uuid

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

log = structlog.get_logger(__name__)

_ROLLBACK_PROCEDURES: dict[str, str] = {
    "RESTART_SERVICE": "Stop service that was restarted; restore original state",
    "CLEAR_CACHE": "Warm cache from backup or let application re-populate",
    "DRAIN_NODE_TRAFFIC": "Re-enable node in load balancer",
    "MODIFY_CONFIG": "Restore previous config from backup",
    "REBOOT_HOST": "Monitor host recovery; escalate if does not come back",
}


class RollbackService:
    """Record and look up rollback procedures for autonomous actions."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def record_executed_action(
        self,
        incident_id: uuid.UUID,
        action_key: str,
        parameters: dict,
        success: bool,
        error: str | None = None,
    ) -> uuid.UUID:
        """Append to autonomous_actions audit table."""
        import json
        from datetime import datetime, timezone
        action_id = uuid.uuid4()
        await self._db.execute(
            text("""
                INSERT INTO autonomous_actions
                    (id, incident_id, action_key, parameters, success, error, executed_at)
                VALUES (:id, :incident_id, :key, :params::jsonb, :success, :error, :now)
            """).bindparams(
                id=action_id,
                incident_id=incident_id,
                key=action_key,
                params=json.dumps(parameters),
                success=success,
                error=error,
                now=datetime.now(timezone.utc),
            )
        )
        return action_id

    def get_rollback_procedure(self, action_key: str) -> str:
        return _ROLLBACK_PROCEDURES.get(action_key, "Manual review required — no automated rollback defined")
