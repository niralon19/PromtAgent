from __future__ import annotations

import uuid

import structlog
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Incident

log = structlog.get_logger(__name__)

_REDIS_KEY_PREFIX = "dedup:fp:"


class DedupService:
    """Detects duplicate alerts using Redis (fast path) with DB fallback."""

    def __init__(self, redis_client=None) -> None:
        self._redis = redis_client

    async def check_duplicate(
        self,
        fingerprint: str,
        db: AsyncSession,
        window_minutes: int = 15,
    ) -> Incident | None:
        """Return the existing active incident if one matches this fingerprint.

        Args:
            fingerprint: Alert fingerprint computed by fingerprint.py
            db: Async DB session.
            window_minutes: How far back to consider an incident "active".

        Returns:
            Existing Incident or None.
        """
        # Fast path: Redis
        if self._redis is not None:
            try:
                cached = await self._redis.get(f"{_REDIS_KEY_PREFIX}{fingerprint}")
                if cached:
                    incident_id = uuid.UUID(cached.decode())
                    result = await db.execute(
                        select(Incident).where(Incident.id == incident_id)
                    )
                    incident = result.scalar_one_or_none()
                    if incident and incident.status not in ("resolved", "false_positive"):
                        log.debug("dedup_hit_redis", fingerprint=fingerprint, incident_id=str(incident_id))
                        return incident
            except Exception as exc:
                log.warning("dedup_redis_error", error=str(exc))

        # DB fallback
        from datetime import datetime, timedelta, timezone
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=window_minutes)

        result = await db.execute(
            select(Incident)
            .where(
                Incident.fingerprint == fingerprint,
                Incident.created_at >= cutoff,
                Incident.status.not_in(["resolved", "false_positive"]),
            )
            .order_by(Incident.created_at.desc())
            .limit(1)
        )
        incident = result.scalar_one_or_none()
        if incident:
            log.debug("dedup_hit_db", fingerprint=fingerprint, incident_id=str(incident.id))
            # Warm Redis cache
            if self._redis is not None:
                try:
                    await self._redis.setex(
                        f"{_REDIS_KEY_PREFIX}{fingerprint}",
                        window_minutes * 60,
                        str(incident.id),
                    )
                except Exception:
                    pass
        return incident

    async def register(
        self,
        fingerprint: str,
        incident_id: uuid.UUID,
        window_minutes: int = 15,
    ) -> None:
        """Register a new incident fingerprint in Redis."""
        if self._redis is None:
            return
        try:
            await self._redis.setex(
                f"{_REDIS_KEY_PREFIX}{fingerprint}",
                window_minutes * 60,
                str(incident_id),
            )
        except Exception as exc:
            log.warning("dedup_register_redis_error", error=str(exc))

    async def increment_recurrence(self, incident: Incident, db: AsyncSession) -> None:
        """Increment recurrence counter on an existing incident."""
        await db.execute(
            update(Incident)
            .where(Incident.id == incident.id)
            .values(recurrence_count=Incident.recurrence_count + 1)
        )
        await db.flush()
        log.info(
            "dedup_recurrence_incremented",
            incident_id=str(incident.id),
            new_count=incident.recurrence_count + 1,
        )
