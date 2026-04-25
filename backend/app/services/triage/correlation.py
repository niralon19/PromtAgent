from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Incident

log = structlog.get_logger(__name__)

_LOCATION_LABELS = ("datacenter", "rack", "switch", "cluster", "region")


class CorrelationService:
    """Groups concurrent alerts that share location and category into parent incidents."""

    async def find_related_incidents(
        self,
        incident: Incident,
        db: AsyncSession,
        window_minutes: int = 10,
    ) -> list[Incident]:
        """Find active incidents that are spatially/temporally related.

        Correlation criteria (all must match):
        - Same category
        - Same datacenter/rack/switch label (if present)
        - Created within `window_minutes`
        - Not the incident itself

        Args:
            incident: The newly-created incident.
            db: Async session.
            window_minutes: Look-back window.

        Returns:
            List of related Incident objects (excluding the input incident).
        """
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=window_minutes)

        result = await db.execute(
            select(Incident).where(
                Incident.id != incident.id,
                Incident.category == incident.category,
                Incident.created_at >= cutoff,
                Incident.status.not_in(["resolved", "false_positive"]),
                Incident.parent_incident_id.is_(None),
            )
        )
        candidates = result.scalars().all()

        related = [c for c in candidates if self._shares_location(incident, c)]
        log.debug(
            "correlation_candidates",
            incident_id=str(incident.id),
            candidate_count=len(candidates),
            related_count=len(related),
        )
        return related

    async def maybe_create_parent(
        self,
        incident: Incident,
        related: list[Incident],
        db: AsyncSession,
        min_group_size: int = 3,
    ) -> Incident | None:
        """If enough related incidents exist, create or assign a parent incident.

        Args:
            incident: The trigger incident.
            related: Related incidents found by find_related_incidents.
            db: Async session.
            min_group_size: Minimum group size to create a parent.

        Returns:
            The parent Incident if created/found, else None.
        """
        group = [incident] + related
        if len(group) < min_group_size:
            return None

        # Check if any already have a parent
        existing_parent_id = next(
            (i.parent_incident_id for i in group if i.parent_incident_id), None
        )
        if existing_parent_id:
            # Link remaining orphans to the existing parent
            for member in group:
                if member.parent_incident_id is None and member.id != existing_parent_id:
                    member.parent_incident_id = existing_parent_id
            await db.flush()
            log.info(
                "correlation_linked_to_existing_parent",
                parent_id=str(existing_parent_id),
                group_size=len(group),
            )
            result = await db.execute(select(Incident).where(Incident.id == existing_parent_id))
            return result.scalar_one_or_none()

        # Create new parent incident
        parent = Incident(
            id=uuid.uuid4(),
            fingerprint=f"parent_{incident.fingerprint}",
            category=incident.category,
            hostname=f"group:{incident.hostname}",
            status="triaging",
            alert_id=incident.alert_id,
            tags=["correlated_group"],
        )
        db.add(parent)
        await db.flush()

        for member in group:
            member.parent_incident_id = parent.id

        await db.flush()
        log.info(
            "correlation_parent_created",
            parent_id=str(parent.id),
            group_size=len(group),
            category=incident.category,
        )
        return parent

    def _shares_location(self, a: Incident, b: Incident) -> bool:
        """Return True if incidents share at least one location label value."""
        labels_a = (a.alert.labels if a.alert else {}) if hasattr(a, "alert") else {}
        labels_b = (b.alert.labels if b.alert else {}) if hasattr(b, "alert") else {}

        # If neither has location labels, correlate by hostname prefix (first segment)
        if not any(k in labels_a for k in _LOCATION_LABELS):
            return a.hostname.split("-")[0] == b.hostname.split("-")[0]

        for label in _LOCATION_LABELS:
            val_a = labels_a.get(label)
            val_b = labels_b.get(label)
            if val_a and val_b and val_a == val_b:
                return True
        return False
