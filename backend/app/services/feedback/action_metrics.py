"""Track action accuracy and usage metrics."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

log = structlog.get_logger(__name__)


async def record_action_outcome(
    db: AsyncSession,
    incident_id: uuid.UUID,
    action_key: str,
    was_correct: bool,
    resolution_time_minutes: int | None = None,
) -> None:
    """Upsert action_metrics row for the given action key."""
    now = datetime.now(timezone.utc)
    try:
        await db.execute(
            text("""
                INSERT INTO action_metrics (action_key, total_uses, correct_uses, last_used_at)
                VALUES (:key, 1, :correct_int, :now)
                ON CONFLICT (action_key) DO UPDATE SET
                    total_uses = action_metrics.total_uses + 1,
                    correct_uses = action_metrics.correct_uses + :correct_int,
                    last_used_at = :now
            """).bindparams(
                key=action_key,
                correct_int=1 if was_correct else 0,
                now=now,
            )
        )

        if resolution_time_minutes is not None:
            await db.execute(
                text("""
                    UPDATE action_metrics
                    SET avg_resolution_minutes = (
                        COALESCE(avg_resolution_minutes, 0) * (total_uses - 1) + :mins
                    ) / total_uses
                    WHERE action_key = :key
                """).bindparams(mins=resolution_time_minutes, key=action_key)
            )
        log.info("action_metrics_updated", action=action_key, correct=was_correct)
    except Exception as exc:
        log.error("action_metrics_update_failed", action=action_key, error=str(exc))
