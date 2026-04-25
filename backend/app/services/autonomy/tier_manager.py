"""TierManager — evaluate and promote/demote action autonomy tiers."""
from __future__ import annotations

from datetime import datetime, timezone

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

log = structlog.get_logger(__name__)

_MIN_USES_FOR_TIER1 = 10
_MIN_ACCURACY_FOR_TIER1 = 0.85
_MIN_USES_FOR_TIER2 = 30
_MIN_ACCURACY_FOR_TIER2 = 0.92


class TierManager:
    """Manage autonomous execution tier assignments for actions."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get_tier(self, action_key: str) -> int:
        """Return current autonomous tier (0 = manual only, 1+ = autonomous)."""
        result = await self._db.execute(
            text("SELECT autonomous_tier FROM action_tier_config WHERE action_key = :key").bindparams(key=action_key)
        )
        row = result.fetchone()
        return row.autonomous_tier if row else 0

    async def evaluate_readiness(self, action_key: str) -> dict:
        """Check if action qualifies for tier promotion based on metrics."""
        result = await self._db.execute(
            text("""
                SELECT total_uses, correct_uses,
                       ROUND(correct_uses::numeric / NULLIF(total_uses,0) * 100, 1) AS accuracy_pct
                FROM action_metrics WHERE action_key = :key
            """).bindparams(key=action_key)
        )
        row = result.fetchone()
        if row is None:
            return {"action_key": action_key, "qualifies": False, "reason": "No usage data"}

        total = row.total_uses or 0
        accuracy = float(row.accuracy_pct or 0) / 100.0

        if total >= _MIN_USES_FOR_TIER2 and accuracy >= _MIN_ACCURACY_FOR_TIER2:
            return {"action_key": action_key, "qualifies": True, "eligible_tier": 2, "accuracy": accuracy, "uses": total}
        if total >= _MIN_USES_FOR_TIER1 and accuracy >= _MIN_ACCURACY_FOR_TIER1:
            return {"action_key": action_key, "qualifies": True, "eligible_tier": 1, "accuracy": accuracy, "uses": total}
        return {
            "action_key": action_key,
            "qualifies": False,
            "reason": f"Uses: {total}/{_MIN_USES_FOR_TIER1}, Accuracy: {accuracy:.0%}/{_MIN_ACCURACY_FOR_TIER1:.0%}",
            "uses": total,
            "accuracy": accuracy,
        }

    async def promote(self, action_key: str, tier: int) -> None:
        """Set autonomous tier for an action."""
        await self._db.execute(
            text("""
                INSERT INTO action_tier_config (action_key, autonomous_tier, promoted_at)
                VALUES (:key, :tier, :now)
                ON CONFLICT (action_key) DO UPDATE SET
                    autonomous_tier = :tier,
                    promoted_at = :now
            """).bindparams(key=action_key, tier=tier, now=datetime.now(timezone.utc))
        )
        log.info("action_promoted", action=action_key, tier=tier)

    async def demote(self, action_key: str) -> None:
        """Reset action to manual-only (tier 0)."""
        await self._db.execute(
            text("""
                UPDATE action_tier_config
                SET autonomous_tier = 0, demoted_at = :now
                WHERE action_key = :key
            """).bindparams(key=action_key, now=datetime.now(timezone.utc))
        )
        log.warning("action_demoted", action=action_key)
