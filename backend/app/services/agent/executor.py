from __future__ import annotations

import uuid
from datetime import datetime, timezone

import structlog
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Incident
from app.services.agent.investigator import InvestigatorAgent
from app.services.agent.parser import InvestigationResult

log = structlog.get_logger(__name__)


class AgentExecutor:
    """Public entry point for running investigations. Handles locking and persistence."""

    def __init__(self, db: AsyncSession, http_client=None, redis_client=None) -> None:
        self._db = db
        self._http_client = http_client
        self._redis = redis_client

    async def run_for_incident(self, incident_id: uuid.UUID) -> InvestigationResult:
        """Run the full investigation pipeline for an incident.

        Prevents double-investigation via a Redis lock (best-effort).
        Persists the agent_run record and updates the incident.

        Args:
            incident_id: UUID of the incident to investigate.

        Returns:
            InvestigationResult.

        Raises:
            ValueError: If incident not found or already investigating.
        """
        bound_log = log.bind(incident_id=str(incident_id))

        # Acquire lock
        lock_acquired = await self._try_lock(incident_id)
        if not lock_acquired:
            bound_log.warning("investigation_already_running")
            raise ValueError(f"Investigation already running for {incident_id}")

        result = await self._db.execute(select(Incident).where(Incident.id == incident_id))
        incident = result.scalar_one_or_none()
        if incident is None:
            await self._release_lock(incident_id)
            raise ValueError(f"Incident {incident_id} not found")

        # Create agent_run record
        run_id = uuid.uuid4()
        started_at = datetime.now(timezone.utc)
        await self._db.execute(
            _insert_agent_run(run_id, incident_id, started_at)
        )
        await self._db.flush()

        # Update incident status
        await self._db.execute(
            update(Incident).where(Incident.id == incident_id).values(status="investigating")
        )
        await self._db.flush()

        try:
            from app.tools.base import ToolContext
            from app.core.config import settings

            ctx = ToolContext(
                incident_id=incident_id,
                correlation_id=str(run_id),
                logger=bound_log,
                http_client=self._http_client,
                db_session=self._db,
                config=settings,
            )

            enrichment = incident.enrichment

            agent = InvestigatorAgent(ctx)
            investigation_result = await agent.investigate(incident, enrichment)

            # Persist investigation result
            await self._db.execute(
                update(Incident)
                .where(Incident.id == incident_id)
                .values(
                    status="open",
                    investigation=investigation_result.model_dump(mode="json"),
                    hypothesis=investigation_result.hypothesis,
                    confidence=investigation_result.confidence,
                    suggested_action_key=investigation_result.suggested_action.action_key,
                )
            )

            # Update agent_run
            await self._db.execute(
                _update_agent_run(run_id, investigation_result, started_at)
            )
            await self._db.flush()

            bound_log.info("agent_executor_completed", confidence=investigation_result.confidence)
            return investigation_result

        except Exception as exc:
            await self._db.execute(
                _fail_agent_run(run_id, str(exc))
            )
            await self._db.execute(
                update(Incident).where(Incident.id == incident_id).values(status="open")
            )
            await self._db.flush()
            bound_log.error("agent_executor_failed", error=str(exc), exc_info=True)
            raise

        finally:
            await self._release_lock(incident_id)

    async def _try_lock(self, incident_id: uuid.UUID) -> bool:
        if self._redis is None:
            return True
        try:
            key = f"agent_lock:{incident_id}"
            result = await self._redis.set(key, "1", nx=True, ex=300)
            return result is not None
        except Exception:
            return True  # Fail open — don't block investigation if Redis is down

    async def _release_lock(self, incident_id: uuid.UUID) -> None:
        if self._redis is None:
            return
        try:
            await self._redis.delete(f"agent_lock:{incident_id}")
        except Exception:
            pass


def _insert_agent_run(run_id: uuid.UUID, incident_id: uuid.UUID, started_at: datetime):
    from sqlalchemy import text
    return text("""
        INSERT INTO agent_runs (id, incident_id, started_at, status)
        VALUES (:id, :incident_id, :started_at, 'running')
    """).bindparams(id=run_id, incident_id=incident_id, started_at=started_at)


def _update_agent_run(run_id: uuid.UUID, result: InvestigationResult, started_at: datetime):
    from sqlalchemy import text
    from datetime import datetime, timezone
    completed_at = datetime.now(timezone.utc)
    return text("""
        UPDATE agent_runs SET
            completed_at=:completed_at,
            iterations=:iterations,
            cost_usd=:cost_usd,
            status='completed'
        WHERE id=:id
    """).bindparams(
        id=run_id,
        completed_at=completed_at,
        iterations=result.iterations_used,
        cost_usd=result.cost_usd,
    )


def _fail_agent_run(run_id: uuid.UUID, error: str):
    from sqlalchemy import text
    return text("""
        UPDATE agent_runs SET status='failed', error=:error WHERE id=:id
    """).bindparams(id=run_id, error=error[:500])
