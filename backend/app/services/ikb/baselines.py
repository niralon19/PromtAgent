from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

import structlog
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

log = structlog.get_logger(__name__)


class MetricBaseline(BaseModel):
    hostname: str
    metric_name: str
    mean: float
    stddev: float
    p50: float
    p95: float
    p99: float
    sample_count: int
    window_days: int
    computed_at: datetime


class BaselineAnalysis(BaseModel):
    current_value: float
    z_score: float
    percentile_rank: float
    is_anomaly: bool
    severity_level: Literal["normal", "mild", "moderate", "severe", "extreme"]
    baseline_ref: MetricBaseline | None = None


def _severity_from_z(z: float) -> Literal["normal", "mild", "moderate", "severe", "extreme"]:
    abs_z = abs(z)
    if abs_z < 2.0:
        return "normal"
    if abs_z < 2.5:
        return "mild"
    if abs_z < 3.0:
        return "moderate"
    if abs_z < 4.0:
        return "severe"
    return "extreme"


class BaselineService:
    """Rolling per-host metric baselines for anomaly detection."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get_baseline(
        self, hostname: str, metric_name: str, window_days: int = 30
    ) -> MetricBaseline | None:
        """Fetch stored baseline for a host+metric combination."""
        result = await self._db.execute(
            text("""
                SELECT hostname, metric_name, mean, stddev, p50, p95, p99,
                       sample_count, window_days, computed_at
                FROM metric_baselines
                WHERE hostname = :hostname AND metric_name = :metric_name
                  AND window_days = :window_days
            """),
            {"hostname": hostname, "metric_name": metric_name, "window_days": window_days},
        )
        row = result.fetchone()
        if row is None:
            return None
        return MetricBaseline(
            hostname=row.hostname,
            metric_name=row.metric_name,
            mean=float(row.mean),
            stddev=float(row.stddev),
            p50=float(row.p50),
            p95=float(row.p95),
            p99=float(row.p99),
            sample_count=int(row.sample_count),
            window_days=int(row.window_days),
            computed_at=row.computed_at,
        )

    async def upsert_baseline(self, baseline: MetricBaseline) -> None:
        """Insert or update a metric baseline record."""
        await self._db.execute(
            text("""
                INSERT INTO metric_baselines
                    (hostname, metric_name, mean, stddev, p50, p95, p99,
                     sample_count, window_days, computed_at)
                VALUES
                    (:hostname, :metric_name, :mean, :stddev, :p50, :p95, :p99,
                     :sample_count, :window_days, :computed_at)
                ON CONFLICT (hostname, metric_name, window_days)
                DO UPDATE SET
                    mean=EXCLUDED.mean, stddev=EXCLUDED.stddev,
                    p50=EXCLUDED.p50, p95=EXCLUDED.p95, p99=EXCLUDED.p99,
                    sample_count=EXCLUDED.sample_count, computed_at=EXCLUDED.computed_at
            """),
            baseline.model_dump(),
        )
        await self._db.flush()

    async def analyze_current_value(
        self,
        hostname: str,
        metric_name: str,
        current_value: float,
        window_days: int = 30,
    ) -> BaselineAnalysis:
        """Compute z-score and anomaly classification for a metric reading.

        Args:
            hostname: Server hostname.
            metric_name: Metric identifier (e.g. 'cpu_pct', 'disk_used_gb').
            current_value: The value triggering the alert.
            window_days: Which baseline window to compare against.

        Returns:
            BaselineAnalysis with z-score, percentile rank, and severity.
        """
        baseline = await self.get_baseline(hostname, metric_name, window_days)
        if baseline is None or baseline.stddev == 0:
            return BaselineAnalysis(
                current_value=current_value,
                z_score=0.0,
                percentile_rank=50.0,
                is_anomaly=False,
                severity_level="normal",
                baseline_ref=baseline,
            )

        z_score = (current_value - baseline.mean) / baseline.stddev

        # Rough percentile rank via known percentile buckets
        if current_value <= baseline.p50:
            pct_rank = 50.0
        elif current_value <= baseline.p95:
            pct_rank = 80.0
        elif current_value <= baseline.p99:
            pct_rank = 97.0
        else:
            pct_rank = 99.5

        severity = _severity_from_z(z_score)
        is_anomaly = abs(z_score) >= 2.5

        return BaselineAnalysis(
            current_value=current_value,
            z_score=round(z_score, 2),
            percentile_rank=pct_rank,
            is_anomaly=is_anomaly,
            severity_level=severity,
            baseline_ref=baseline,
        )
