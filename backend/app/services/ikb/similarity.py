from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import structlog
from pydantic import BaseModel
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Incident
from app.services.ikb.embeddings import EmbeddingService
from app.services.ikb.incident_embedder import build_embedding_text

log = structlog.get_logger(__name__)


class SimilarIncident(BaseModel):
    incident_id: uuid.UUID
    hostname: str
    category: str | None
    alertname: str | None
    similarity_score: float
    resolution_category: str | None
    was_hypothesis_correct: str | None
    resolution_time_minutes: int | None
    hypothesis: str | None
    created_at: datetime


class SimilarityService:
    """Semantic similarity search over resolved incidents using pgvector."""

    def __init__(self, embedding_service: EmbeddingService, db: AsyncSession) -> None:
        self._svc = embedding_service
        self._db = db

    async def find_similar_incidents(
        self,
        incident: Incident,
        limit: int = 5,
        category_filter: str | None = None,
        min_age_days: int = 1,
        resolved_only: bool = True,
    ) -> list[SimilarIncident]:
        """Find semantically similar past incidents.

        Args:
            incident: The current incident to compare against.
            limit: Max results.
            category_filter: Restrict to a specific category.
            min_age_days: Exclude very recent incidents (avoid self-match).
            resolved_only: Only return incidents with resolution data.

        Returns:
            List of SimilarIncident ordered by similarity (descending).
        """
        text_repr = build_embedding_text(incident)
        query_vector = await self._svc.embed(text_repr)

        # Build pgvector query
        vector_str = "[" + ",".join(str(v) for v in query_vector) + "]"
        cutoff = datetime.now(timezone.utc) - timedelta(days=min_age_days)

        conditions = [
            "embedding IS NOT NULL",
            f"id != '{incident.id}'",
            f"created_at < '{cutoff.isoformat()}'",
        ]
        if resolved_only:
            conditions.append("status = 'resolved'")
            conditions.append("resolution IS NOT NULL")
        if category_filter:
            conditions.append(f"category = '{category_filter}'")

        where_clause = " AND ".join(conditions)

        sql = text(f"""
            SELECT
                id,
                hostname,
                category,
                investigation->>'hypothesis' AS hypothesis,
                resolution->>'resolution_category' AS resolution_category,
                resolution->>'was_hypothesis_correct' AS was_hypothesis_correct,
                (resolution->>'resolution_time_minutes')::int AS resolution_time_minutes,
                created_at,
                1 - (embedding <=> '{vector_str}'::vector) AS similarity_score
            FROM incidents
            WHERE {where_clause}
            ORDER BY embedding <=> '{vector_str}'::vector
            LIMIT :limit
        """)

        try:
            result = await self._db.execute(sql, {"limit": limit})
            rows = result.fetchall()
        except Exception as exc:
            # pgvector not installed or embedding column missing
            log.error("similarity_search_failed", error=str(exc))
            return []

        similar = []
        for row in rows:
            similar.append(
                SimilarIncident(
                    incident_id=row.id,
                    hostname=row.hostname,
                    category=row.category,
                    alertname=None,
                    similarity_score=float(row.similarity_score or 0),
                    resolution_category=row.resolution_category,
                    was_hypothesis_correct=row.was_hypothesis_correct,
                    resolution_time_minutes=row.resolution_time_minutes,
                    hypothesis=row.hypothesis,
                    created_at=row.created_at,
                )
            )

        log.debug("similarity_search_results", count=len(similar), incident_id=str(incident.id))
        return similar
