"""APScheduler jobs for feedback loop maintenance."""
from __future__ import annotations

import structlog
from sqlalchemy import text

log = structlog.get_logger(__name__)


async def run_daily_host_stats(db_factory) -> None:
    """Refresh host_statistics for all hosts with recent activity."""
    from app.services.feedback.host_statistics import update_host_statistics

    async with db_factory() as db:
        result = await db.execute(
            text("""
                SELECT DISTINCT hostname FROM incidents
                WHERE created_at >= NOW() - INTERVAL '7 days'
                  AND hostname IS NOT NULL
            """)
        )
        hostnames = [r.hostname for r in result.fetchall()]

    log.info("daily_host_stats_started", host_count=len(hostnames))
    for hostname in hostnames:
        async with db_factory() as db:
            try:
                await update_host_statistics(db, hostname)
                await db.commit()
            except Exception as exc:
                log.error("daily_host_stats_failed", hostname=hostname, error=str(exc))


async def run_weekly_pattern_detection(db_factory) -> None:
    """Detect weekly patterns and write dashboard_alerts."""
    from app.services.feedback.pattern_detector import detect_weekly_patterns, upsert_dashboard_alert

    async with db_factory() as db:
        patterns = await detect_weekly_patterns(db)
        for p in patterns[:20]:
            title = f"Recurring: {p['hostname']} / {p['category']}"
            desc = f"{p['count']} incidents in 90 days. Common action: {p.get('common_action', 'N/A')}"
            await upsert_dashboard_alert(
                db,
                alert_type="recurring_pattern",
                title=title,
                description=desc,
                severity="warning" if p["count"] < 10 else "critical",
                metadata=p,
            )
        await db.commit()
    log.info("weekly_pattern_detection_complete", patterns_found=len(patterns))


async def run_monthly_cleanup(db_factory) -> None:
    """Remove processed_resolution_events older than 6 months."""
    async with db_factory() as db:
        result = await db.execute(
            text("""
                DELETE FROM processed_resolution_events
                WHERE processed_at < NOW() - INTERVAL '6 months'
            """)
        )
        await db.commit()
        log.info("monthly_cleanup_complete", deleted=result.rowcount)
