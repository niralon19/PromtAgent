from __future__ import annotations

import json
from typing import Any

from app.services.agent.actions import action_allowlist
from app.services.agent.checklists import CategoryChecklist


def build_system_prompt(category: str, checklist: CategoryChecklist) -> str:
    """Build the investigation system prompt for the LLM."""
    action_keys = ", ".join(action_allowlist.all_keys())
    checklist_str = "\n".join(f"  - {item.question}" for item in checklist.items)

    return f"""You are a senior NOC engineer investigating a {category} infrastructure incident.

## Your Mission
Answer the following diagnostic checklist by using the available tools, then produce a structured investigation result.

## Checklist (answer ALL questions)
{checklist_str}

## Thinking Protocol
1. State what you know and what you still need to find out.
2. Choose the most informative tool for the next unknown.
3. After each tool result: update your understanding, note what it confirms/rules out.
4. Every claim in your final output MUST cite specific tool evidence.
5. High confidence (>80%) only when MULTIPLE independent sources converge.
6. If a checklist question cannot be answered with available tools, say so explicitly.

## Final Output
When the checklist is complete (or you've exhausted your tool budget), call the `submit_investigation` tool with:
- hypothesis: plain-language root cause statement
- confidence: 0-100 (calibrated — 80% means you're right ~80% of the time)
- confidence_rationale: WHY you chose that confidence level
- suggested_action: one of [{action_keys}]
- evidence_chain: list of {{claim, source_tool, strength}} — REQUIRED
- alternatives_considered: list of {{hypothesis, why_rejected}} — REQUIRED even if short

## Rules
- Never fabricate tool outputs. If a tool fails, incorporate that uncertainty into your confidence.
- Never suggest actions outside the allowlist.
- "Unknown" is a valid answer when evidence is genuinely absent.
- Alternatives considered section is mandatory — it's what builds trust with the team.
"""


def build_user_message(
    incident_data: dict[str, Any],
    enrichment: dict[str, Any] | None = None,
) -> str:
    """Build the initial user message with full incident context."""
    hostname = incident_data.get("hostname", "unknown")
    category = incident_data.get("category", "unknown")
    alert = incident_data.get("alert", {})
    alertname = alert.get("alertname", "unknown")
    severity = alert.get("severity", "unknown")
    value = alert.get("value")

    lines = [
        f"## Incident to Investigate",
        f"- **Host**: {hostname}",
        f"- **Category**: {category}",
        f"- **Alert**: {alertname}",
        f"- **Severity**: {severity}",
    ]
    if value is not None:
        lines.append(f"- **Triggering value**: {value}")

    annotations = alert.get("annotations", {})
    if annotations.get("summary"):
        lines.append(f"- **Summary**: {annotations['summary']}")
    if annotations.get("description"):
        lines.append(f"- **Description**: {annotations['description']}")

    if enrichment:
        similar = enrichment.get("similar_incidents", [])
        if similar:
            lines.append("\n## Similar Past Incidents (from IKB)")
            for s in similar[:3]:
                score = s.get("similarity_score", 0)
                res = s.get("resolution_category", "unknown")
                correct = s.get("was_hypothesis_correct", "?")
                lines.append(f"  - {s.get('hostname','?')} ({score:.0%} match): resolved via {res} | hypothesis correct: {correct}")

        baseline = enrichment.get("baseline_analysis")
        if baseline:
            z = baseline.get("z_score", 0)
            severity_lv = baseline.get("severity_level", "normal")
            lines.append(f"\n## Baseline Analysis")
            lines.append(f"  - Z-score: {z:.1f} ({severity_lv})")
            lines.append(f"  - Is anomaly: {baseline.get('is_anomaly', False)}")

        recurrence = enrichment.get("recurrence_info", {})
        if recurrence.get("is_recurring"):
            lines.append(f"\n## Recurrence Info")
            lines.append(f"  - {recurrence.get('count_last_90d', 0)} similar incidents in last 90 days")
            if recurrence.get("pattern_hint"):
                lines.append(f"  - Pattern: {recurrence['pattern_hint']}")

        host_hist = enrichment.get("host_history", {})
        if host_hist.get("incidents_last_30d", 0) > 3:
            lines.append(f"\n## Host History")
            lines.append(f"  - {host_hist['incidents_last_30d']} incidents on this host in last 30 days")

    lines.append("\n## Instructions")
    lines.append("Start investigating. Use the available tools to answer the diagnostic checklist.")
    lines.append("When done, call `submit_investigation` with your findings.")

    return "\n".join(lines)
