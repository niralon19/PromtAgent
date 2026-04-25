"""Autonomy management API."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db

router = APIRouter(prefix="/api/v1/autonomy", tags=["autonomy"])

_KILL_SWITCH_KEY = "autonomy:kill_switch"


@router.get("/tiers")
async def get_tiers(db: AsyncSession = Depends(get_db)) -> list[dict[str, Any]]:
    """Return all action tier assignments."""
    result = await db.execute(
        text("""
            SELECT action_key, autonomous_tier, promoted_at,
                   COALESCE(demoted_at::text, '') AS demoted_at
            FROM action_tier_config
            ORDER BY autonomous_tier DESC, action_key
        """)
    )
    return [dict(r._mapping) for r in result.fetchall()]


@router.post("/kill-switch")
async def toggle_kill_switch(
    body: dict[str, Any],
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Enable or disable the global autonomous execution kill switch."""
    enabled = bool(body.get("enabled", True))
    # Store in DB as a simple config row (Redis dependency optional)
    await db.execute(
        text("""
            INSERT INTO action_tier_config (action_key, autonomous_tier)
            VALUES ('__kill_switch__', :val)
            ON CONFLICT (action_key) DO UPDATE SET autonomous_tier = :val
        """).bindparams(val=1 if enabled else 0)
    )
    await db.commit()
    return {"kill_switch_enabled": enabled}


@router.get("/kill-switch")
async def get_kill_switch(db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    result = await db.execute(
        text("SELECT autonomous_tier FROM action_tier_config WHERE action_key = '__kill_switch__'")
    )
    row = result.fetchone()
    return {"kill_switch_enabled": bool(row and row.autonomous_tier == 1)}


@router.get("/shadow-queue")
async def shadow_queue(
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """Return recent shadow-mode decisions for review."""
    result = await db.execute(
        text("""
            SELECT id, incident_id, action_key, parameters, confidence, hypothesis, created_at
            FROM shadow_mode_decisions
            ORDER BY created_at DESC
            LIMIT :lim
        """).bindparams(lim=limit)
    )
    return [dict(r._mapping) for r in result.fetchall()]


@router.get("/audit")
async def audit_log(
    action_key: str | None = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """Return autonomous action audit log."""
    base = "SELECT * FROM autonomous_actions"
    params: dict = {"lim": limit}
    if action_key:
        base += " WHERE action_key = :key"
        params["key"] = action_key
    base += " ORDER BY executed_at DESC LIMIT :lim"
    result = await db.execute(text(base).bindparams(**params))
    return [dict(r._mapping) for r in result.fetchall()]


@router.post("/rollback/{action_id}")
async def rollback_action(action_id: str, db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    """Initiate a rollback for a specific autonomous action."""
    result = await db.execute(
        text("SELECT * FROM autonomous_actions WHERE id = :id").bindparams(id=action_id)
    )
    row = result.fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Action not found")

    from app.services.autonomy.rollback import RollbackService
    svc = RollbackService(db)
    procedure = svc.get_rollback_procedure(row.action_key)

    return {
        "action_id": action_id,
        "action_key": row.action_key,
        "rollback_procedure": procedure,
        "status": "rollback_initiated",
    }
