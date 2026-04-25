"""Tests for InvestigatorAgent and AgentExecutor."""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.agent.investigator import InvestigatorAgent
from app.services.agent.parser import InvestigationResult
from app.tools.base import ToolContext


def _make_ctx() -> ToolContext:
    import structlog
    from app.core.config import settings

    return ToolContext(
        incident_id=uuid.uuid4(),
        correlation_id=str(uuid.uuid4()),
        logger=structlog.get_logger("test"),
        http_client=None,
        db_session=MagicMock(),
        config=settings,
    )


def _make_incident(category: str = "physical") -> MagicMock:
    alert = MagicMock()
    alert.alertname = "HighCPU"
    alert.severity = "critical"
    alert.value = 95.2
    alert.annotations = {"summary": "CPU over threshold"}

    incident = MagicMock()
    incident.id = uuid.uuid4()
    incident.hostname = "server-01"
    incident.category = category
    incident.alert = alert
    incident.enrichment = None
    return incident


def _submit_tool_block(data: dict) -> MagicMock:
    block = MagicMock()
    block.type = "tool_use"
    block.name = "submit_investigation"
    block.id = "tool_" + str(uuid.uuid4())
    block.input = data
    return block


def _final_result_raw() -> dict:
    return {
        "hypothesis": "CPU spike caused by runaway process",
        "confidence": 82,
        "confidence_rationale": "Multiple tools confirm high CPU from single PID",
        "suggested_action": {
            "action_key": "NOTE_IN_TICKET",
            "parameters": {},
            "rationale": "Log for review",
        },
        "evidence_chain": [
            {"claim": "PID 1234 using 90% CPU", "source_tool": "ssh_check_processes", "strength": "strong"}
        ],
        "alternatives_considered": [
            {"hypothesis": "Scheduled job", "why_rejected": "No cron at this time"}
        ],
    }


def _mock_response(stop_reason: str, content: list, input_tokens: int = 100, output_tokens: int = 50) -> MagicMock:
    resp = MagicMock()
    resp.stop_reason = stop_reason
    resp.content = content
    resp.usage = MagicMock()
    resp.usage.input_tokens = input_tokens
    resp.usage.output_tokens = output_tokens
    return resp


@pytest.mark.asyncio
async def test_investigate_submit_on_first_tool_use():
    ctx = _make_ctx()
    incident = _make_incident()

    submit_block = _submit_tool_block(_final_result_raw())
    response = _mock_response("tool_use", [submit_block])

    with patch("anthropic.AsyncAnthropic") as MockClient:
        mock_messages = AsyncMock()
        mock_messages.create = AsyncMock(return_value=response)
        MockClient.return_value.messages = mock_messages

        agent = InvestigatorAgent(ctx)
        result = await agent.investigate(incident)

    assert isinstance(result, InvestigationResult)
    assert result.confidence == 82
    assert result.hypothesis == "CPU spike caused by runaway process"
    assert result.suggested_action.action_key == "NOTE_IN_TICKET"
    assert result.iterations_used == 1


@pytest.mark.asyncio
async def test_investigate_tool_loop_then_submit():
    ctx = _make_ctx()
    incident = _make_incident()

    tool_block = MagicMock()
    tool_block.type = "tool_use"
    tool_block.name = "grafana_query"
    tool_block.id = "tool_abc"
    tool_block.input = {"hostname": "server-01", "metric": "cpu_usage", "range_minutes": 30}

    first_response = _mock_response("tool_use", [tool_block])
    submit_block = _submit_tool_block(_final_result_raw())
    second_response = _mock_response("tool_use", [submit_block])

    with patch("anthropic.AsyncAnthropic") as MockClient:
        mock_messages = AsyncMock()
        mock_messages.create = AsyncMock(side_effect=[first_response, second_response])
        MockClient.return_value.messages = mock_messages

        with patch("app.services.agent.investigator.execute_anthropic_tool_call") as mock_exec:
            mock_exec.return_value = {"output": "cpu=90%", "duration_ms": 100}
            agent = InvestigatorAgent(ctx)
            result = await agent.investigate(incident)

    assert result.iterations_used == 2
    assert result.confidence == 82


@pytest.mark.asyncio
async def test_investigate_end_turn_without_submit():
    ctx = _make_ctx()
    incident = _make_incident()

    text_block = MagicMock()
    text_block.type = "text"
    text_block.text = "I conclude the investigation."

    response = _mock_response("end_turn", [text_block])

    with patch("anthropic.AsyncAnthropic") as MockClient:
        mock_messages = AsyncMock()
        mock_messages.create = AsyncMock(return_value=response)
        MockClient.return_value.messages = mock_messages

        agent = InvestigatorAgent(ctx)
        result = await agent.investigate(incident)

    assert result.confidence == 10
    assert "did not reach a conclusion" in result.hypothesis


@pytest.mark.asyncio
async def test_investigate_budget_exceeded():
    ctx = _make_ctx()
    incident = _make_incident()

    text_block = MagicMock()
    text_block.type = "text"
    text_block.text = "thinking..."

    # Response that would cost a lot (large token counts)
    response = _mock_response("tool_use", [text_block], input_tokens=500_000, output_tokens=100_000)

    with patch("anthropic.AsyncAnthropic") as MockClient:
        mock_messages = AsyncMock()
        mock_messages.create = AsyncMock(return_value=response)
        MockClient.return_value.messages = mock_messages

        agent = InvestigatorAgent(ctx)
        result = await agent.investigate(incident)

    # Should still return a fallback result
    assert isinstance(result, InvestigationResult)
    assert result.cost_usd > 0.0


@pytest.mark.asyncio
async def test_investigate_cost_tracked():
    ctx = _make_ctx()
    incident = _make_incident()

    submit_block = _submit_tool_block(_final_result_raw())
    response = _mock_response("tool_use", [submit_block], input_tokens=1000, output_tokens=500)

    with patch("anthropic.AsyncAnthropic") as MockClient:
        mock_messages = AsyncMock()
        mock_messages.create = AsyncMock(return_value=response)
        MockClient.return_value.messages = mock_messages

        agent = InvestigatorAgent(ctx)
        result = await agent.investigate(incident)

    # cost = (1000*3 + 500*15) / 1_000_000 = 0.0105
    assert result.cost_usd > 0.0
    assert result.duration_seconds >= 0.0


@pytest.mark.asyncio
async def test_investigate_with_enrichment():
    ctx = _make_ctx()
    incident = _make_incident()

    enrichment = {
        "similar_incidents": [
            {"hostname": "server-02", "similarity_score": 0.92, "resolution_category": "process_kill", "was_hypothesis_correct": True}
        ],
        "baseline_analysis": {"z_score": 3.5, "severity_level": "critical", "is_anomaly": True},
        "recurrence_info": {"is_recurring": True, "count_last_90d": 5, "pattern_hint": "every Monday morning"},
        "host_history": {"incidents_last_30d": 8},
    }

    submit_block = _submit_tool_block(_final_result_raw())
    response = _mock_response("tool_use", [submit_block])

    with patch("anthropic.AsyncAnthropic") as MockClient:
        mock_messages = AsyncMock()
        mock_messages.create = AsyncMock(return_value=response)
        MockClient.return_value.messages = mock_messages

        agent = InvestigatorAgent(ctx)
        result = await agent.investigate(incident, enrichment=enrichment)

    assert result.confidence == 82
    # Verify enrichment was included in prompt (by checking call args)
    call_kwargs = mock_messages.create.call_args[1]
    first_user_msg = call_kwargs["messages"][0]["content"]
    assert "Similar Past Incidents" in first_user_msg or "Baseline" in first_user_msg


@pytest.mark.asyncio
async def test_investigate_invalid_action_key_defaults():
    ctx = _make_ctx()
    incident = _make_incident()

    raw = _final_result_raw()
    raw["suggested_action"]["action_key"] = "TOTALLY_FAKE_ACTION"

    submit_block = _submit_tool_block(raw)
    response = _mock_response("tool_use", [submit_block])

    with patch("anthropic.AsyncAnthropic") as MockClient:
        mock_messages = AsyncMock()
        mock_messages.create = AsyncMock(return_value=response)
        MockClient.return_value.messages = mock_messages

        agent = InvestigatorAgent(ctx)
        result = await agent.investigate(incident)

    assert result.suggested_action.action_key == "NOTE_IN_TICKET"


@pytest.mark.asyncio
async def test_investigate_max_iterations_respected():
    ctx = _make_ctx()
    incident = _make_incident()

    tool_block = MagicMock()
    tool_block.type = "tool_use"
    tool_block.name = "grafana_query"
    tool_block.id = "tool_loop"
    tool_block.input = {}

    loop_response = _mock_response("tool_use", [tool_block])

    with patch("anthropic.AsyncAnthropic") as MockClient:
        mock_messages = AsyncMock()
        # Always return loop_response — never submit
        mock_messages.create = AsyncMock(return_value=loop_response)
        MockClient.return_value.messages = mock_messages

        with patch("app.services.agent.investigator.execute_anthropic_tool_call") as mock_exec:
            mock_exec.return_value = {"output": "data", "duration_ms": 10}
            agent = InvestigatorAgent(ctx)
            result = await agent.investigate(incident)

    # Should have hit max_iterations limit
    max_iter = 8  # default
    assert result.iterations_used <= max_iter
    assert isinstance(result, InvestigationResult)
