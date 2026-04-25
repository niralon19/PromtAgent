"""Detect and flag recurring incident patterns."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

log = structlog.get_logger(__name__)

_RECURRENCE_WINDOW_DAYS = 90
_RECURRENCE_THRESHOLD = 3


async def detect_recurrence(
    db: AsyncSession,
    incident_id: uuid.UUID,
    hostname: str,
    category: str,
) -> dict:
    """Check whether this incident is part of a recurring pattern.

    Returns a dict with: is_recurring, count_last_90d, pattern_hint.
    """
    since = datetime.now(timezone.utc) - timedelta(days=_RECURRENCE_WINDOW_DAYS)
    try:
        result = await db.execute(
            text("""
                SELECT COUNT(*) AS cnt,
                       MIN(created_at) AS first_seen,
                       MAX(created_at) AS last_seen
                FROM incidents
                WHERE hostname = :hostname
                  AND category = :category
                  AND created_at >= :since
                  AND id != :incident_id
            """).bindparams(
                hostname=hostname,
                category=category,
                since=since,
                incident_id=incident_id,
            )
        )
        row = result.fetchone()
        count = row.cnt if row else 0
        is_recurring = count >= _RECURRENCE_THRESHOLD

        pattern_hint = None
        if is_recurring and row and row.first_seen and row.last_seen:
            span_days = (row.last_seen - row.first_seen).days or 1
            freq = count / (span_days / 7.0)
            pattern_hint = f"~{freq:.1f}x per week over {span_days} days"

        return {
            "is_recurring": is_recurring,
            "count_last_90d": count,
            "pattern_hint": pattern_hint,
        }
    except Exception as exc:
        log.error("recurrence_detection_failed", incident_id=str(incident_id), error=str(exc))
        return {"is_recurring": False, "count_last_90d": 0, "pattern_hint": None}
