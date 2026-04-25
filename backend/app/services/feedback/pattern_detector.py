"""Weekly pattern detection across resolved incidents."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

log = structlog.get_logger(__name__)


async def detect_weekly_patterns(db: AsyncSession) -> list[dict]:
    """Identify top recurring (hostname, category) pairs from the last 90 days.

    Returns a list of pattern dicts: hostname, category, count, last_seen.
    """
    since = datetime.now(timezone.utc) - timedelta(days=90)
    try:
        result = await db.execute(
            text("""
                SELECT hostname, category,
                       COUNT(*) AS incident_count,
                       MAX(created_at) AS last_seen,
                       MODE() WITHIN GROUP (ORDER BY suggested_action_key) AS common_action
                FROM incidents
                WHERE created_at >= :since
                  AND status IN ('resolved', 'false_positive')
                GROUP BY hostname, category
                HAVING COUNT(*) >= 3
                ORDER BY incident_count DESC
                LIMIT 50
            """).bindparams(since=since)
        )
        rows = result.fetchall()
        return [
            {
                "hostname": r.hostname,
                "category": r.category,
                "count": r.incident_count,
                "last_seen": r.last_seen.isoformat() if r.last_seen else None,
                "common_action": r.common_action,
            }
            for r in rows
        ]
    except Exception as exc:
        log.error("pattern_detection_failed", error=str(exc))
        return []


async def upsert_dashboard_alert(
    db: AsyncSession,
    alert_type: str,
    title: str,
    description: str,
    severity: str = "warning",
    metadata: dict | None = None,
) -> None:
    """Insert or update a dashboard alert for recurring pattern findings."""
    now = datetime.now(timezone.utc)
    try:
        import json
        await db.execute(
            text("""
                INSERT INTO dashboard_alerts (alert_type, title, description, severity, metadata, created_at, updated_at)
                VALUES (:type, :title, :desc, :severity, :meta::jsonb, :now, :now)
                ON CONFLICT (alert_type, title) DO UPDATE SET
                    description = EXCLUDED.description,
                    severity = EXCLUDED.severity,
                    metadata = EXCLUDED.metadata,
                    updated_at = EXCLUDED.updated_at
            """).bindparams(
                type=alert_type,
                title=title,
                desc=description,
                severity=severity,
                meta=json.dumps(metadata or {}),
                now=now,
            )
        )
    except Exception as exc:
        log.error("dashboard_alert_upsert_failed", error=str(exc))
