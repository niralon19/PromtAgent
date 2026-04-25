"""Knowledge Explorer API — search, annotations, patterns, insights."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db

router = APIRouter(prefix="/api/v1/knowledge", tags=["knowledge"])


@router.get("/search")
async def search_incidents(
    q: str = Query(""),
    category: str | None = Query(None),
    hostname: str | None = Query(None),
    resolution_category: str | None = Query(None),
    limit: int = Query(20, le=100),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """Hybrid full-text + vector search over resolved incidents."""
    base = """
        SELECT i.id, i.hostname, i.category, i.status,
               i.hypothesis, i.confidence, i.suggested_action_key,
               i.resolution_category, i.was_hypothesis_correct,
               i.resolution_time_minutes, i.created_at,
               a.alertname, a.severity
        FROM incidents i
        LEFT JOIN alerts a ON a.id = i.alert_id
        WHERE i.status IN ('resolved', 'false_positive')
    """
    params: dict = {"limit": limit}
    filters = ""

    if q:
        filters += " AND (i.hypothesis ILIKE :q_like OR a.alertname ILIKE :q_like OR i.hostname ILIKE :q_like)"
        params["q_like"] = f"%{q}%"
    if category:
        filters += " AND i.category = :category"
        params["category"] = category
    if hostname:
        filters += " AND i.hostname ILIKE :hostname_like"
        params["hostname_like"] = f"%{hostname}%"
    if resolution_category:
        filters += " AND i.resolution_category = :res_cat"
        params["res_cat"] = resolution_category

    sql = base + filters + " ORDER BY i.created_at DESC LIMIT :limit"
    result = await db.execute(text(sql).bindparams(**params))
    return [dict(r._mapping) for r in result.fetchall()]


@router.get("/incidents/{incident_id}")
async def knowledge_incident(incident_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    result = await db.execute(
        text("""
            SELECT i.*, a.alertname, a.severity, a.annotations, a.labels
            FROM incidents i
            LEFT JOIN alerts a ON a.id = i.alert_id
            WHERE i.id = :id
        """).bindparams(id=incident_id)
    )
    row = result.fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Incident not found")
    return dict(row._mapping)


@router.post("/incidents/{incident_id}/annotations")
async def add_annotation(
    incident_id: uuid.UUID,
    body: dict[str, Any],
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Add a human annotation (Teach Mode) to a resolved incident."""
    note = body.get("note", "")
    correct_action = body.get("correct_action_key")
    tags = body.get("tags", [])

    updates: dict[str, Any] = {}
    if note:
        updates["resolution_details"] = note
    if correct_action:
        updates["suggested_action_key"] = correct_action
    if tags:
        updates["tags"] = tags

    if updates:
        set_parts = ", ".join(f"{k} = :{k}" for k in updates)
        updates["id"] = incident_id
        await db.execute(
            text(f"UPDATE incidents SET {set_parts} WHERE id = :id").bindparams(**updates)
        )
        await db.commit()

    return {"incident_id": str(incident_id), "updated": list(updates.keys())}


@router.get("/patterns")
async def knowledge_patterns(
    limit: int = Query(20, le=100),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    result = await db.execute(
        text("""
            SELECT hostname, category, COUNT(*) AS count,
                   MODE() WITHIN GROUP (ORDER BY resolution_category) AS common_resolution,
                   MAX(created_at) AS last_seen
            FROM incidents
            WHERE status IN ('resolved', 'false_positive')
              AND created_at >= NOW() - INTERVAL '180 days'
            GROUP BY hostname, category
            HAVING COUNT(*) >= 2
            ORDER BY count DESC
            LIMIT :lim
        """).bindparams(lim=limit)
    )
    return [dict(r._mapping) for r in result.fetchall()]


@router.get("/insights")
async def knowledge_insights(db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    """Aggregate insights: top hosts, action distribution, category breakdown."""
    top_hosts = await db.execute(
        text("""
            SELECT hostname, COUNT(*) AS incident_count,
                   ROUND(AVG(confidence)::numeric, 1) AS avg_confidence
            FROM incidents
            WHERE hostname IS NOT NULL
            GROUP BY hostname
            ORDER BY incident_count DESC
            LIMIT 10
        """)
    )

    action_dist = await db.execute(
        text("""
            SELECT suggested_action_key, COUNT(*) AS count
            FROM incidents
            WHERE suggested_action_key IS NOT NULL
            GROUP BY suggested_action_key
            ORDER BY count DESC
        """)
    )

    category_breakdown = await db.execute(
        text("""
            SELECT category, COUNT(*) AS total,
                   COUNT(*) FILTER (WHERE status = 'resolved') AS resolved
            FROM incidents
            GROUP BY category
        """)
    )

    return {
        "top_hosts": [dict(r._mapping) for r in top_hosts.fetchall()],
        "action_distribution": [dict(r._mapping) for r in action_dist.fetchall()],
        "category_breakdown": [dict(r._mapping) for r in category_breakdown.fetchall()],
    }
