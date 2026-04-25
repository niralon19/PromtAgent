"""Feedback metrics API endpoints."""
from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db

router = APIRouter(prefix="/api/v1", tags=["feedback"])


@router.get("/metrics/actions")
async def get_action_metrics(db: AsyncSession = Depends(get_db)) -> list[dict[str, Any]]:
    """Return accuracy and usage stats for all action keys."""
    result = await db.execute(
        text("""
            SELECT action_key, total_uses, correct_uses, avg_resolution_minutes, last_used_at,
                   CASE WHEN total_uses > 0
                        THEN ROUND(correct_uses::numeric / total_uses * 100, 1)
                        ELSE 0 END AS accuracy_pct
            FROM action_metrics
            ORDER BY total_uses DESC
        """)
    )
    rows = result.fetchall()
    return [dict(r._mapping) for r in rows]


@router.get("/metrics/hosts/{hostname}")
async def get_host_metrics(hostname: str, db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    """Return statistics for a specific host."""
    result = await db.execute(
        text("""
            SELECT hostname, total_incidents, open_incidents, avg_resolution_minutes,
                   most_common_category, last_incident_at, updated_at
            FROM host_statistics
            WHERE hostname = :hostname
        """).bindparams(hostname=hostname)
    )
    row = result.fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail=f"No statistics found for host {hostname!r}")
    return dict(row._mapping)


@router.get("/patterns/recent")
async def get_recent_patterns(
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """Return recently detected recurring patterns."""
    result = await db.execute(
        text("""
            SELECT hostname, category, COUNT(*) AS count,
                   MAX(created_at) AS last_seen,
                   MODE() WITHIN GROUP (ORDER BY suggested_action_key) AS common_action
            FROM incidents
            WHERE created_at >= NOW() - INTERVAL '90 days'
              AND status IN ('resolved', 'false_positive')
            GROUP BY hostname, category
            HAVING COUNT(*) >= 3
            ORDER BY count DESC
            LIMIT :lim
        """).bindparams(lim=limit)
    )
    return [dict(r._mapping) for r in result.fetchall()]


@router.get("/recurrence/active")
async def get_active_recurrences(
    min_count: int = 3,
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """Return hosts with active recurring incidents (not yet resolved)."""
    result = await db.execute(
        text("""
            SELECT hostname, category, COUNT(*) AS open_count,
                   MIN(created_at) AS first_open
            FROM incidents
            WHERE status NOT IN ('resolved', 'false_positive')
            GROUP BY hostname, category
            HAVING COUNT(*) >= :min_count
            ORDER BY open_count DESC
        """).bindparams(min_count=min_count)
    )
    return [dict(r._mapping) for r in result.fetchall()]


@router.get("/dashboard/alerts")
async def get_dashboard_alerts(db: AsyncSession = Depends(get_db)) -> list[dict[str, Any]]:
    """Return active dashboard alerts (recurring patterns, anomalies)."""
    result = await db.execute(
        text("""
            SELECT alert_type, title, description, severity, metadata, created_at, updated_at
            FROM dashboard_alerts
            ORDER BY updated_at DESC
            LIMIT 50
        """)
    )
    return [dict(r._mapping) for r in result.fetchall()]
