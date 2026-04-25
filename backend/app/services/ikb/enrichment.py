from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import structlog
from pydantic import BaseModel
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Incident
from app.services.ikb.baselines import BaselineAnalysis, BaselineService
from app.services.ikb.embeddings import EmbeddingService
from app.services.ikb.similarity import SimilarIncident, SimilarityService

log = structlog.get_logger(__name__)


class HostHistory(BaseModel):
    hostname: str
    total_incidents: int
    incidents_last_30d: int
    incidents_last_7d: int
    most_common_resolution: str | None


class RecurrenceInfo(BaseModel):
    is_recurring: bool
    count_last_90d: int
    previous_resolutions: list[str]
    pattern_hint: str | None


class EnrichmentContext(BaseModel):
    similar_incidents: list[SimilarIncident]
    host_history: HostHistory
    baseline_analysis: BaselineAnalysis | None
    related_active_incident_ids: list[uuid.UUID]
    recurrence_info: RecurrenceInfo


class EnrichmentService:
    """Assembles full contextual enrichment for an incident before investigation."""

    def __init__(
        self,
        embedding_svc: EmbeddingService,
        db: AsyncSession,
        redis_client=None,
    ) -> None:
        self._sim = SimilarityService(embedding_svc, db)
        self._baseline = BaselineService(db)
        self._db = db
        self._redis = redis_client

    async def enrich(self, incident: Incident) -> EnrichmentContext:
        """Gather all contextual enrichment in parallel.

        Args:
            incident: The triaged incident to enrich.

        Returns:
            EnrichmentContext with all available context populated.

        Raises:
            IKBUnavailableError: Only if DB is unreachable (extremely rare).
        """
        bound_log = log.bind(incident_id=str(incident.id), hostname=incident.hostname)
        bound_log.info("enrichment_started")

        similar_task = asyncio.create_task(
            self._sim.find_similar_incidents(incident, limit=5)
        )
        host_history_task = asyncio.create_task(
            self._get_host_history(incident.hostname)
        )
        related_task = asyncio.create_task(
            self._get_related_active(incident)
        )
        recurrence_task = asyncio.create_task(
            self._get_recurrence_info(incident)
        )

        similar, host_history, related_ids, recurrence = await asyncio.gather(
            similar_task,
            host_history_task,
            related_task,
            recurrence_task,
            return_exceptions=True,
        )

        # Baseline analysis (needs alert value)
        baseline_analysis: BaselineAnalysis | None = None
        if incident.alert and incident.alert.value is not None:
            try:
                metric_name = _guess_metric_name(incident.alert.alertname, incident.alert.labels or {})
                baseline_analysis = await self._baseline.analyze_current_value(
                    incident.hostname, metric_name, incident.alert.value
                )
            except Exception as exc:
                bound_log.warning("baseline_analysis_failed", error=str(exc))

        ctx = EnrichmentContext(
            similar_incidents=similar if not isinstance(similar, BaseException) else [],
            host_history=host_history if not isinstance(host_history, BaseException) else HostHistory(
                hostname=incident.hostname, total_incidents=0,
                incidents_last_30d=0, incidents_last_7d=0, most_common_resolution=None,
            ),
            baseline_analysis=baseline_analysis,
            related_active_incident_ids=related_ids if not isinstance(related_ids, BaseException) else [],
            recurrence_info=recurrence if not isinstance(recurrence, BaseException) else RecurrenceInfo(
                is_recurring=False, count_last_90d=0, previous_resolutions=[], pattern_hint=None
            ),
        )

        # Persist enrichment on the incident
        await self._db.execute(
            update(Incident)
            .where(Incident.id == incident.id)
            .values(enrichment=ctx.model_dump(mode="json"))
        )
        await self._db.flush()

        bound_log.info(
            "enrichment_completed",
            similar_count=len(ctx.similar_incidents),
            is_recurring=ctx.recurrence_info.is_recurring,
        )
        return ctx

    async def _get_host_history(self, hostname: str) -> HostHistory:
        now = datetime.now(timezone.utc)
        result = await self._db.execute(
            select(
                func.count(Incident.id).label("total"),
                func.count(Incident.id).filter(
                    Incident.created_at >= now - timedelta(days=30)
                ).label("last_30d"),
                func.count(Incident.id).filter(
                    Incident.created_at >= now - timedelta(days=7)
                ).label("last_7d"),
            ).where(Incident.hostname == hostname)
        )
        row = result.one()

        # Most common resolution
        res_result = await self._db.execute(
            select(
                Incident.resolution["resolution_category"].as_string().label("res_cat"),
                func.count().label("cnt"),
            )
            .where(
                Incident.hostname == hostname,
                Incident.status == "resolved",
            )
            .group_by("res_cat")
            .order_by(func.count().desc())
            .limit(1)
        )
        top_res = res_result.fetchone()

        return HostHistory(
            hostname=hostname,
            total_incidents=row.total or 0,
            incidents_last_30d=row.last_30d or 0,
            incidents_last_7d=row.last_7d or 0,
            most_common_resolution=top_res.res_cat if top_res else None,
        )

    async def _get_related_active(self, incident: Incident) -> list[uuid.UUID]:
        """Return IDs of other currently active incidents on the same host."""
        result = await self._db.execute(
            select(Incident.id).where(
                Incident.hostname == incident.hostname,
                Incident.id != incident.id,
                Incident.status.not_in(["resolved", "false_positive"]),
            ).limit(10)
        )
        return [row[0] for row in result.fetchall()]

    async def _get_recurrence_info(self, incident: Incident) -> RecurrenceInfo:
        cutoff = datetime.now(timezone.utc) - timedelta(days=90)
        result = await self._db.execute(
            select(Incident).where(
                Incident.hostname == incident.hostname,
                Incident.category == incident.category,
                Incident.created_at >= cutoff,
                Incident.id != incident.id,
            ).order_by(Incident.created_at.desc())
        )
        past = result.scalars().all()
        resolutions = [
            i.resolution.get("resolution_category")
            for i in past
            if i.resolution and i.resolution.get("resolution_category")
        ]

        is_recurring = len(past) >= 2
        pattern_hint: str | None = None
        if is_recurring and resolutions:
            most_common = max(set(resolutions), key=resolutions.count)
            pattern_hint = f"Recurring {incident.category} issue; most common resolution: {most_common}"

        return RecurrenceInfo(
            is_recurring=is_recurring,
            count_last_90d=len(past),
            previous_resolutions=list(dict.fromkeys(resolutions))[:5],
            pattern_hint=pattern_hint,
        )


def _guess_metric_name(alertname: str, labels: dict[str, str]) -> str:
    """Infer a metric name from the alert to look up baselines."""
    name = alertname.lower()
    for keyword in ("cpu", "memory", "disk", "io", "load", "temperature", "swap"):
        if keyword in name:
            return keyword
    return labels.get("__name__", alertname.lower())
