from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import structlog
from pydantic import BaseModel, ValidationError

from app.services.agent.actions import SuggestedAction, action_allowlist

log = structlog.get_logger(__name__)


class Evidence(BaseModel):
    claim: str
    source_tool: str
    source_output_ref: str = ""
    strength: str = "moderate"


class Alternative(BaseModel):
    hypothesis: str
    why_rejected: str
    evidence_against: list[str] = []


class InvestigationResult(BaseModel):
    hypothesis: str
    confidence: int
    confidence_rationale: str
    suggested_action: SuggestedAction
    evidence_chain: list[Evidence]
    alternatives_considered: list[Alternative]
    tools_executed_summary: list[str] = []
    iterations_used: int = 0
    cost_usd: float = 0.0
    duration_seconds: float = 0.0
    checklist_completion: dict[str, bool] = {}
    completed_at: datetime = None  # type: ignore[assignment]

    def model_post_init(self, __context: Any) -> None:
        if self.completed_at is None:
            object.__setattr__(self, "completed_at", datetime.now(timezone.utc))


def parse_submit_investigation(raw: dict[str, Any]) -> InvestigationResult:
    """Parse the submit_investigation tool input into InvestigationResult.

    Validates and normalizes the agent's final output.
    """
    hypothesis = raw.get("hypothesis", "Unknown — investigation incomplete")
    confidence = int(raw.get("confidence", 0))
    confidence_rationale = raw.get("confidence_rationale", "")

    # Parse suggested action
    action_raw = raw.get("suggested_action", {})
    action_key = action_raw.get("action_key", "NOTE_IN_TICKET")
    if not action_allowlist.is_valid(action_key):
        log.warning("invalid_action_key_defaulting", key=action_key)
        action_key = "NOTE_IN_TICKET"

    defn = action_allowlist.get(action_key)
    suggested_action = SuggestedAction(
        action_key=action_key,
        parameters=action_raw.get("parameters", {}),
        rationale=action_raw.get("rationale", ""),
        estimated_risk=defn.estimated_risk if defn else "low",
        requires_approval=defn.requires_approval if defn else True,
        tier=defn.tier if defn else 0,
    )

    # Parse evidence chain
    evidence_chain = [
        Evidence(
            claim=e.get("claim", ""),
            source_tool=e.get("source_tool", "unknown"),
            strength=e.get("strength", "moderate"),
        )
        for e in raw.get("evidence_chain", [])
    ]

    # Parse alternatives
    alternatives = [
        Alternative(
            hypothesis=a.get("hypothesis", ""),
            why_rejected=a.get("why_rejected", ""),
        )
        for a in raw.get("alternatives_considered", [])
    ]

    return InvestigationResult(
        hypothesis=hypothesis,
        confidence=max(0, min(100, confidence)),
        confidence_rationale=confidence_rationale,
        suggested_action=suggested_action,
        evidence_chain=evidence_chain,
        alternatives_considered=alternatives,
    )
