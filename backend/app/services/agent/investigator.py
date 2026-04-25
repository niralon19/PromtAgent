from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone
from typing import Any

import structlog

from app.core.config import settings
from app.db.models import Incident
from app.services.agent.checklists import CategoryChecklist
from app.services.agent.parser import InvestigationResult, parse_submit_investigation
from app.services.agent.prompts import build_system_prompt, build_user_message
from app.services.agent.tool_adapter import execute_anthropic_tool_call, tools_for_anthropic
from app.tools.base import ToolContext

log = structlog.get_logger(__name__)

# Token cost estimates for claude-sonnet-4-6 (approximate)
_INPUT_COST_PER_M = 3.0
_OUTPUT_COST_PER_M = 15.0


def _estimate_cost(input_tokens: int, output_tokens: int) -> float:
    return (input_tokens * _INPUT_COST_PER_M + output_tokens * _OUTPUT_COST_PER_M) / 1_000_000


class InvestigatorAgent:
    """Active investigation agent using Anthropic tool-use loop."""

    def __init__(self, ctx: ToolContext) -> None:
        self._ctx = ctx

    async def investigate(
        self,
        incident: Incident,
        enrichment: dict | None = None,
    ) -> InvestigationResult:
        """Run the bounded investigation loop.

        Args:
            incident: The incident to investigate.
            enrichment: Pre-computed EnrichmentContext dict (optional).

        Returns:
            InvestigationResult with hypothesis, confidence, evidence, actions.
        """
        import anthropic

        category = incident.category or "physical"
        checklist = CategoryChecklist(category)
        bound_log = self._ctx.logger.bind(
            incident_id=str(incident.id),
            category=category,
        )
        bound_log.info("investigation_started")

        start_time = time.monotonic()
        client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

        incident_data: dict[str, Any] = {
            "id": str(incident.id),
            "hostname": incident.hostname,
            "category": category,
            "alert": {
                "alertname": incident.alert.alertname if incident.alert else "unknown",
                "severity": incident.alert.severity if incident.alert else "warning",
                "value": incident.alert.value if incident.alert else None,
                "annotations": dict(incident.alert.annotations or {}) if incident.alert else {},
            },
        }

        system_prompt = build_system_prompt(category, checklist)
        user_msg = build_user_message(incident_data, enrichment)

        messages: list[dict[str, Any]] = [{"role": "user", "content": user_msg}]
        tools = tools_for_anthropic(category)

        max_iterations = getattr(settings, "agent_max_iterations", 8)
        budget_usd = getattr(settings, "agent_budget_usd", 0.50)
        model = getattr(settings, "agent_model", "claude-sonnet-4-6")

        total_input_tokens = 0
        total_output_tokens = 0
        tools_executed: list[str] = []
        final_result_raw: dict | None = None
        iterations_used = 0

        for iteration in range(max_iterations):
            iterations_used = iteration + 1
            bound_log.debug("investigation_iteration", iteration=iteration)

            response = await client.messages.create(
                model=model,
                system=system_prompt,
                messages=messages,
                tools=tools,
                max_tokens=getattr(settings, "agent_max_tokens", 4096),
            )

            total_input_tokens += response.usage.input_tokens
            total_output_tokens += response.usage.output_tokens
            current_cost = _estimate_cost(total_input_tokens, total_output_tokens)

            if current_cost > budget_usd:
                bound_log.warning("investigation_budget_exceeded", cost=current_cost)
                break

            messages.append({"role": "assistant", "content": response.content})

            if response.stop_reason == "end_turn":
                bound_log.info("investigation_end_turn")
                break

            if response.stop_reason == "tool_use":
                tool_results = []
                for block in response.content:
                    if block.type == "tool_use":
                        tools_executed.append(block.name)

                        if block.name == "submit_investigation":
                            final_result_raw = block.input
                            bound_log.info("investigation_submit_called", iteration=iteration)
                            break

                        result = await execute_anthropic_tool_call(block, self._ctx)
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": str(result),
                        })

                if final_result_raw is not None:
                    break

                if tool_results:
                    messages.append({"role": "user", "content": tool_results})
                    checklist.update_from_tool_results(tool_results)

                if checklist.is_complete():
                    messages.append({
                        "role": "user",
                        "content": (
                            "The diagnostic checklist is now complete. "
                            "Please call `submit_investigation` with your final assessment."
                        ),
                    })

        duration_seconds = time.monotonic() - start_time
        cost_usd = _estimate_cost(total_input_tokens, total_output_tokens)

        if final_result_raw is None:
            bound_log.warning("investigation_no_submit_called")
            final_result_raw = {
                "hypothesis": "Investigation did not reach a conclusion within budget",
                "confidence": 10,
                "confidence_rationale": "Loop ended without submit_investigation call",
                "suggested_action": {"action_key": "ESCALATE_TO_TIER2", "parameters": {}, "rationale": "Needs human review"},
                "evidence_chain": [],
                "alternatives_considered": [],
            }

        result = parse_submit_investigation(final_result_raw)
        result.iterations_used = iterations_used
        result.cost_usd = round(cost_usd, 4)
        result.duration_seconds = round(duration_seconds, 2)
        result.tools_executed_summary = list(dict.fromkeys(tools_executed))
        result.checklist_completion = checklist.completion_dict()

        bound_log.info(
            "investigation_completed",
            confidence=result.confidence,
            cost_usd=result.cost_usd,
            iterations=result.iterations_used,
            action=result.suggested_action.action_key,
        )
        return result
