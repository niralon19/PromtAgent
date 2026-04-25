from __future__ import annotations

import structlog

from app.services.jira.client import JiraClient

log = structlog.get_logger(__name__)


async def poll_resolved_issues() -> None:
    """Polling fallback: check Jira for recently-resolved NOC issues every 5 minutes.

    Catches resolutions that may have been missed by the webhook.
    Idempotent: JiraSyncHandler skips already-resolved incidents.
    """
    from app.core.config import settings
    from app.db.session import AsyncSessionLocal
    from app.services.jira.sync_handler import JiraSyncHandler

    project = settings.jira_project_key or "NOC"
    jql = (
        f'project = {project} AND status in ("Resolved", "Done", "Closed") '
        f'AND updated >= "-15m" ORDER BY updated DESC'
    )

    client = JiraClient()
    try:
        issues = await client.search_issues(jql, fields=["status", "customfield_incident_id"])
    except Exception as exc:
        log.error("jira_polling_failed", error=str(exc))
        return

    if not issues:
        return

    log.info("jira_polling_found_resolved", count=len(issues))

    async with AsyncSessionLocal() as db:
        for issue in issues:
            try:
                issue_key = issue.get("key", "")
                fields = issue.get("fields", {})
                handler = JiraSyncHandler(db)
                await handler.handle_resolution(issue_key, fields)
                await db.commit()
            except Exception as exc:
                await db.rollback()
                log.error("jira_polling_issue_failed", issue=issue.get("key"), error=str(exc))
