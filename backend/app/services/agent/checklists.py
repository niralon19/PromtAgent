from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


@dataclass
class ChecklistItem:
    question: str
    answered: bool = False
    answer_evidence: list[str] = field(default_factory=list)


Category = Literal["physical", "data_integrity", "coupling"]

_CHECKLISTS: dict[str, list[str]] = {
    "physical": [
        "What resource is the bottleneck (CPU, memory, disk, IO)?",
        "What process or service is consuming it?",
        "When did the issue start?",
        "Is the issue still active or self-resolved?",
        "Is there a historical pattern of this issue on this host?",
    ],
    "data_integrity": [
        "Where exactly are the data stopping (source, pipeline, sink)?",
        "Is the data source still producing records?",
        "When was the last valid record received?",
        "Are there errors visible in the pipeline logs?",
        "Is this a source failure or a sink/consumer failure?",
    ],
    "coupling": [
        "Which side of the link/session failed first?",
        "How long has the link been down?",
        "Are there other nearby devices with the same issue?",
        "Is there a known maintenance window that could explain this?",
        "Is the neighboring device/peer known and expected?",
    ],
}


class CategoryChecklist:
    """Tracks answered/unanswered questions for a given incident category."""

    def __init__(self, category: str) -> None:
        questions = _CHECKLISTS.get(category, _CHECKLISTS["physical"])
        self.items = [ChecklistItem(question=q) for q in questions]

    def is_complete(self) -> bool:
        return all(item.answered for item in self.items)

    def next_unanswered(self) -> str | None:
        for item in self.items:
            if not item.answered:
                return item.question
        return None

    def mark_answered(self, question: str, evidence: list[str]) -> None:
        for item in self.items:
            if item.question == question:
                item.answered = True
                item.answer_evidence.extend(evidence)
                return

    def completion_dict(self) -> dict[str, bool]:
        return {item.question: item.answered for item in self.items}

    def update_from_tool_results(self, tool_results: list[dict]) -> None:
        """Heuristically mark questions answered based on successful tool results.

        This is a best-effort pass; the LLM is the authoritative judge.
        """
        successful = [r for r in tool_results if not r.get("is_error")]
        if not successful:
            return
        for item in self.items:
            if not item.answered and successful:
                item.answered = True
                item.answer_evidence.append(f"Answered by tool output (heuristic)")
                break
