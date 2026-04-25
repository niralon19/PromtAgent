from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class JiraTicketContent(BaseModel):
    summary: str
    description_adf: dict[str, Any]
    custom_fields: dict[str, Any]


def _adf_text(text: str) -> dict[str, Any]:
    return {"type": "text", "text": text}


def _adf_paragraph(*texts: str) -> dict[str, Any]:
    return {"type": "paragraph", "content": [_adf_text(t) for t in texts]}


def _adf_heading(text: str, level: int = 2) -> dict[str, Any]:
    return {
        "type": "heading",
        "attrs": {"level": level},
        "content": [_adf_text(text)],
    }


def _adf_bullet_list(items: list[str]) -> dict[str, Any]:
    return {
        "type": "bulletList",
        "content": [
            {
                "type": "listItem",
                "content": [_adf_paragraph(item)],
            }
            for item in items
        ],
    }


def _adf_rule() -> dict[str, Any]:
    return {"type": "rule"}


def _confidence_bar(confidence: int) -> str:
    filled = confidence // 10
    bar = "█" * filled + "░" * (10 - filled)
    return f"Confidence: [{bar}] {confidence}%"


def build_ticket_content(
    incident_data: dict[str, Any],
    investigation: dict[str, Any] | None = None,
    enrichment: dict[str, Any] | None = None,
) -> JiraTicketContent:
    """Build Jira ADF ticket content from incident and investigation data.

    Args:
        incident_data: Serialized Incident dict.
        investigation: InvestigationResult dict (may be None if not yet investigated).
        enrichment: EnrichmentContext dict (optional).

    Returns:
        JiraTicketContent with summary, ADF description, and custom fields.
    """
    hostname = incident_data.get("hostname", "unknown")
    category = incident_data.get("category", "unknown")
    severity = incident_data.get("alert", {}).get("severity", "warning") if incident_data.get("alert") else "warning"
    alertname = incident_data.get("alert", {}).get("alertname", "Alert") if incident_data.get("alert") else "Alert"

    hypothesis = (investigation or {}).get("hypothesis", "Under investigation")
    confidence = (investigation or {}).get("confidence", 0)
    suggested_action = (investigation or {}).get("suggested_action", {})
    evidence_chain = (investigation or {}).get("evidence_chain", [])
    alternatives = (investigation or {}).get("alternatives_considered", [])

    # Summary: short, scannable
    conf_label = f"{confidence}%" if investigation else "?"
    summary = f"[AUTO][{severity.upper()}] {hypothesis[:80]} — {hostname} ({conf_label})"

    # Build ADF document
    content: list[dict[str, Any]] = [
        _adf_heading("🔍 TL;DR", 2),
        _adf_paragraph(hypothesis),
        _adf_paragraph(_confidence_bar(confidence)),
        _adf_rule(),
        _adf_heading("📋 Incident Details", 2),
        _adf_bullet_list([
            f"Host: {hostname}",
            f"Category: {category}",
            f"Alert: {alertname}",
            f"Severity: {severity}",
        ]),
    ]

    if evidence_chain:
        content.append(_adf_heading("🔗 Evidence Chain", 2))
        content.append(
            _adf_bullet_list(
                [f"[{e.get('strength', '?').upper()}] {e.get('claim', '')}" for e in evidence_chain]
            )
        )

    if suggested_action:
        action_key = suggested_action.get("action_key", "N/A")
        rationale = suggested_action.get("rationale", "")
        content.append(_adf_heading("⚡ Suggested Action", 2))
        content.append(_adf_paragraph(f"Action: {action_key}"))
        if rationale:
            content.append(_adf_paragraph(f"Rationale: {rationale}"))

    if alternatives:
        content.append(_adf_heading("🤔 Alternatives Considered", 2))
        content.append(
            _adf_bullet_list(
                [f"{a.get('hypothesis', '')}: {a.get('why_rejected', '')}" for a in alternatives]
            )
        )

    # Historical context from IKB
    similar = (enrichment or {}).get("similar_incidents", []) if enrichment else []
    if similar:
        content.append(_adf_heading("📚 Similar Past Incidents", 2))
        content.append(
            _adf_bullet_list(
                [
                    f"{s.get('hostname', '?')} — {s.get('resolution_category', 'unknown')} "
                    f"({s.get('similarity_score', 0):.0%} match)"
                    for s in similar[:5]
                ]
            )
        )

    content.append(_adf_rule())
    content.append(_adf_heading("✅ Resolution (to be filled by engineer)", 2))
    content.append(
        _adf_bullet_list([
            "Actual resolution category: [select from dropdown]",
            "Was hypothesis correct?: [Yes / Partially / No]",
            "Actual action taken: [describe]",
            "Notes: [any relevant context]",
        ])
    )

    description_adf: dict[str, Any] = {
        "version": 1,
        "type": "doc",
        "content": content,
    }

    from app.core.config import settings
    field_ids: dict[str, str] = getattr(settings, "jira_custom_field_ids", {}) or {}

    custom_fields: dict[str, Any] = {
        field_ids.get("incident_id", "customfield_incident_id"): str(incident_data.get("id", "")),
        field_ids.get("category", "customfield_category"): category,
        field_ids.get("confidence", "customfield_confidence"): confidence,
        field_ids.get("hypothesis", "customfield_hypothesis"): hypothesis,
        field_ids.get("suggested_action", "customfield_suggested_action"): (
            suggested_action.get("action_key", "") if suggested_action else ""
        ),
    }

    return JiraTicketContent(
        summary=summary,
        description_adf=description_adf,
        custom_fields=custom_fields,
    )
