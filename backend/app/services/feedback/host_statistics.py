"""Update per-host incident statistics after resolution."""
from __future__ import annotations

from datetime import datetime, timezone

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

log = structlog.get_logger(__name__)


async def update_host_statistics(db: AsyncSession, hostname: str) -> None:
    """Recompute and upsert host_statistics for the given hostname."""
    now = datetime.now(timezone.utc)
    try:
        await db.execute(
            text("""
                INSERT INTO host_statistics (
                    hostname, total_incidents, open_incidents,
                    avg_resolution_minutes, most_common_category,
                    last_incident_at, updated_at
                )
                SELECT
                    hostname,
                    COUNT(*) AS total_incidents,
                    COUNT(*) FILTER (WHERE status NOT IN ('resolved', 'false_positive')) AS open_incidents,
                    AVG(resolution_time_minutes) AS avg_resolution_minutes,
                    MODE() WITHIN GROUP (ORDER BY category) AS most_common_category,
                    MAX(created_at) AS last_incident_at,
                    :now AS updated_at
                FROM incidents
                WHERE hostname = :hostname
                GROUP BY hostname
                ON CONFLICT (hostname) DO UPDATE SET
                    total_incidents = EXCLUDED.total_incidents,
                    open_incidents = EXCLUDED.open_incidents,
                    avg_resolution_minutes = EXCLUDED.avg_resolution_minutes,
                    most_common_category = EXCLUDED.most_common_category,
                    last_incident_at = EXCLUDED.last_incident_at,
                    updated_at = EXCLUDED.updated_at
            """).bindparams(hostname=hostname, now=now)
        )
        log.info("host_statistics_updated", hostname=hostname)
    except Exception as exc:
        log.error("host_statistics_update_failed", hostname=hostname, error=str(exc))
