"""AutonomousExecutor — gate-checked execution of remediations."""
from __future__ import annotations

import uuid

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.autonomy.circuit_breaker import CircuitBreaker
from app.services.autonomy.rollback import RollbackService
from app.services.autonomy.shadow_mode import ShadowExecutor
from app.services.autonomy.tier_manager import TierManager

log = structlog.get_logger(__name__)

_KILL_SWITCH_KEY = "autonomy:kill_switch"
_MIN_CONFIDENCE_FOR_AUTO = 80


class AutonomousExecutor:
    """Evaluate all gates and conditionally execute autonomous remediations."""

    def __init__(self, db: AsyncSession, redis_client=None) -> None:
        self._db = db
        self._redis = redis_client
        self._tier_mgr = TierManager(db)
        self._cb = CircuitBreaker(redis_client)
        self._shadow = ShadowExecutor(db)
        self._rollback = RollbackService(db)

    async def maybe_execute(
        self,
        incident_id: uuid.UUID,
        action_key: str,
        parameters: dict,
        confidence: int,
        hostname: str,
        hypothesis: str,
    ) -> dict:
        """Check all gates and execute if allowed.

        Returns a dict: {executed, reason, action_id?, rollback_procedure?}
        """
        bound_log = log.bind(
            incident_id=str(incident_id), action=action_key, hostname=hostname
        )

        # Gate 1: Global kill switch
        if await self._kill_switch_active():
            bound_log.info("autonomy_kill_switch_active")
            await self._shadow.record(incident_id, action_key, parameters, confidence, hypothesis)
            return {"executed": False, "reason": "kill_switch", "shadow": True}

        # Gate 2: Action must have autonomous tier assigned
        tier = await self._tier_mgr.get_tier(action_key)
        if tier < 1:
            bound_log.debug("autonomy_action_not_enabled", tier=tier)
            await self._shadow.record(incident_id, action_key, parameters, confidence, hypothesis)
            return {"executed": False, "reason": "not_autonomous_tier", "shadow": True}

        # Gate 3: Confidence threshold
        if confidence < _MIN_CONFIDENCE_FOR_AUTO:
            bound_log.info("autonomy_confidence_too_low", confidence=confidence)
            return {"executed": False, "reason": f"confidence_below_{_MIN_CONFIDENCE_FOR_AUTO}"}

        # Gate 4: Circuit breaker
        if await self._cb.is_open(action_key, hostname):
            bound_log.warning("autonomy_circuit_breaker_open")
            return {"executed": False, "reason": "circuit_breaker_open"}

        # All gates passed — execute
        bound_log.info("autonomy_executing")
        success = False
        error_msg = None
        try:
            # Actual execution would call the tool here; placeholder for now
            success = True
            bound_log.info("autonomy_execution_succeeded")
        except Exception as exc:
            error_msg = str(exc)
            bound_log.error("autonomy_execution_failed", error=error_msg)
            await self._cb.record_failure(action_key, hostname)

        action_id = await self._rollback.record_executed_action(
            incident_id, action_key, parameters, success, error_msg
        )
        await self._db.commit()

        return {
            "executed": True,
            "success": success,
            "action_id": str(action_id),
            "rollback_procedure": self._rollback.get_rollback_procedure(action_key),
        }

    async def _kill_switch_active(self) -> bool:
        if self._redis is None:
            return False
        try:
            val = await self._redis.get(_KILL_SWITCH_KEY)
            return val == b"1" or val == "1"
        except Exception:
            return False
