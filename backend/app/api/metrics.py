"""Metrics and system health API."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db
from app.db.session import engine

router = APIRouter(prefix="/api/v1", tags=["metrics"])


@router.get("/metrics/quality")
async def quality_metrics(db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    """Agent hypothesis accuracy and action effectiveness."""
    result = await db.execute(
        text("""
            SELECT
                COUNT(*) FILTER (WHERE was_hypothesis_correct IS NOT NULL) AS evaluated_count,
                COUNT(*) FILTER (WHERE was_hypothesis_correct = TRUE) AS correct_count,
                ROUND(AVG(confidence) FILTER (WHERE confidence IS NOT NULL), 1) AS avg_confidence,
                ROUND(AVG(resolution_time_minutes) FILTER (WHERE resolution_time_minutes IS NOT NULL), 0) AS avg_resolution_minutes,
                COUNT(*) FILTER (WHERE status = 'false_positive') AS false_positives,
                COUNT(*) AS total
            FROM incidents
        """)
    )
    row = result.fetchone()
    r = dict(row._mapping) if row else {}

    evaluated = r.get("evaluated_count") or 0
    correct = r.get("correct_count") or 0
    accuracy = round(correct / evaluated * 100, 1) if evaluated > 0 else None

    return {
        "hypothesis_accuracy_pct": accuracy,
        "evaluated_count": evaluated,
        "avg_confidence": r.get("avg_confidence"),
        "avg_resolution_minutes": r.get("avg_resolution_minutes"),
        "false_positive_count": r.get("false_positives"),
        "total_incidents": r.get("total"),
    }


@router.get("/metrics/operational")
async def operational_metrics(db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    """Throughput, investigation rate, cost totals."""
    result = await db.execute(
        text("""
            SELECT
                COUNT(*) AS total_runs,
                COUNT(*) FILTER (WHERE status = 'completed') AS completed_runs,
                COUNT(*) FILTER (WHERE status = 'failed') AS failed_runs,
                ROUND(SUM(cost_usd)::numeric, 4) AS total_cost_usd,
                ROUND(AVG(iterations)::numeric, 1) AS avg_iterations,
                ROUND(AVG(EXTRACT(EPOCH FROM (completed_at - started_at)))::numeric, 1) AS avg_duration_seconds
            FROM agent_runs
        """)
    )
    row = result.fetchone()
    return dict(row._mapping) if row else {}


@router.get("/metrics/autonomy-candidates")
async def autonomy_candidates(
    min_uses: int = 10,
    min_accuracy: float = 0.85,
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """Action keys that qualify for autonomous tier promotion."""
    result = await db.execute(
        text("""
            SELECT
                action_key,
                total_uses,
                correct_uses,
                ROUND(correct_uses::numeric / NULLIF(total_uses, 0) * 100, 1) AS accuracy_pct,
                avg_resolution_minutes
            FROM action_metrics
            WHERE total_uses >= :min_uses
              AND (correct_uses::float / NULLIF(total_uses, 0)) >= :min_accuracy
            ORDER BY accuracy_pct DESC
        """).bindparams(min_uses=min_uses, min_accuracy=min_accuracy)
    )
    return [dict(r._mapping) for r in result.fetchall()]


@router.post("/actions/{action_key}/promote")
async def promote_action(action_key: str, db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    """Admin: record that an action has been promoted to a higher autonomy tier."""
    await db.execute(
        text("""
            INSERT INTO action_tier_config (action_key, autonomous_tier, promoted_at)
            VALUES (:key, 1, NOW())
            ON CONFLICT (action_key) DO UPDATE SET
                autonomous_tier = action_tier_config.autonomous_tier + 1,
                promoted_at = NOW()
        """).bindparams(key=action_key)
    )
    await db.commit()
    return {"action_key": action_key, "promoted": True}


@router.get("/system/health")
async def system_health() -> dict[str, Any]:
    """System component health check."""
    db_ok = False
    try:
        async with engine.connect() as conn:
            from sqlalchemy import text as _text
            await conn.execute(_text("SELECT 1"))
        db_ok = True
    except Exception:
        pass

    return {
        "database": "ok" if db_ok else "error",
        "status": "ok" if db_ok else "degraded",
    }
