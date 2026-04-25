from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.tools.base import Tool, ToolContext, ToolInput, ToolOutput
from app.tools.executor import execute_tool
from app.tools.registry import ToolRegistry, register_tool, tool_registry


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


class EchoInput(ToolInput):
    message: str


class EchoOutput(ToolOutput):
    echoed: str


class EchoTool(Tool):
    name = "test_echo"
    description = "Echo back the input message."
    categories = ["physical", "coupling"]
    input_model = EchoInput
    output_model = EchoOutput
    timeout_seconds = 5
    safety_level = "read_only"

    async def execute(self, input: EchoInput, ctx: ToolContext) -> EchoOutput:
        return EchoOutput(echoed=input.message)


class SlowInput(ToolInput):
    delay: float = 99.0


class SlowOutput(ToolOutput):
    done: bool = False


class SlowTool(Tool):
    name = "test_slow"
    description = "Sleeps forever."
    categories = ["physical"]
    input_model = SlowInput
    output_model = SlowOutput
    timeout_seconds = 1
    safety_level = "read_only"

    async def execute(self, input: SlowInput, ctx: ToolContext) -> SlowOutput:
        import asyncio
        await asyncio.sleep(input.delay)
        return SlowOutput(done=True)


def _make_ctx(db_session: Any = None) -> ToolContext:
    mock_session = db_session or AsyncMock()
    mock_session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None)))
    return ToolContext(
        incident_id=uuid.uuid4(),
        correlation_id="test-corr-01",
        logger=MagicMock(bind=MagicMock(return_value=MagicMock(
            info=MagicMock(), warning=MagicMock(), error=MagicMock(), debug=MagicMock()
        ))),
        http_client=AsyncMock(),
        db_session=mock_session,
        config=MagicMock(),
    )


# ---------------------------------------------------------------------------
# Registry tests
# ---------------------------------------------------------------------------


def test_register_and_get() -> None:
    registry = ToolRegistry()
    registry.register(EchoTool)
    tool = registry.get("test_echo")
    assert tool.name == "test_echo"


def test_get_unknown_raises_keyerror() -> None:
    registry = ToolRegistry()
    with pytest.raises(KeyError, match="not registered"):
        registry.get("does_not_exist")


def test_list_for_category() -> None:
    registry = ToolRegistry()
    registry.register(EchoTool)
    physical_tools = registry.list_for_category("physical")
    assert any(t.name == "test_echo" for t in physical_tools)
    # EchoTool is NOT in data_integrity
    di_tools = registry.list_for_category("data_integrity")
    assert not any(t.name == "test_echo" for t in di_tools)


def test_schemas_for_llm() -> None:
    registry = ToolRegistry()
    registry.register(EchoTool)
    schemas = registry.list_all_schemas_for_llm()
    echo_schema = next((s for s in schemas if s["name"] == "test_echo"), None)
    assert echo_schema is not None
    assert "input_schema" in echo_schema
    assert echo_schema["input_schema"]["properties"]["message"]


def test_decorator_registers_on_global_registry() -> None:
    # Use a fresh name to avoid collision with session-scoped registry
    @register_tool
    class UniqueTestTool(Tool):
        name = "unique_test_tool_abc123"
        description = "Test"
        categories = ["physical"]
        input_model = EchoInput
        output_model = EchoOutput
        timeout_seconds = 5
        safety_level = "read_only"

        async def execute(self, input, ctx):
            return EchoOutput(echoed="x")

    assert tool_registry.get("unique_test_tool_abc123") is not None


# ---------------------------------------------------------------------------
# Executor tests
# ---------------------------------------------------------------------------


async def test_executor_success() -> None:
    registry = ToolRegistry()
    registry.register(EchoTool)

    # Patch global registry temporarily
    import app.tools.executor as exec_module
    original = exec_module.tool_registry

    try:
        exec_module.tool_registry = registry
        ctx = _make_ctx()
        record = await execute_tool("test_echo", {"message": "hello"}, ctx)
        assert record.status == "success"
        assert record.output == {"echoed": "hello"}
        assert record.duration_ms >= 0
    finally:
        exec_module.tool_registry = original


async def test_executor_timeout() -> None:
    registry = ToolRegistry()
    registry.register(SlowTool)

    import app.tools.executor as exec_module
    original = exec_module.tool_registry

    try:
        exec_module.tool_registry = registry
        ctx = _make_ctx()
        record = await execute_tool("test_slow", {"delay": 99.0}, ctx)
        assert record.status == "timeout"
        assert "Timed out" in (record.error or "")
    finally:
        exec_module.tool_registry = original


async def test_executor_invalid_input_raises() -> None:
    registry = ToolRegistry()
    registry.register(EchoTool)

    import app.tools.executor as exec_module
    from app.core.errors import ToolExecutionError
    original = exec_module.tool_registry

    try:
        exec_module.tool_registry = registry
        ctx = _make_ctx()
        with pytest.raises(ToolExecutionError):
            await execute_tool("test_echo", {"wrong_field": 123}, ctx)
    finally:
        exec_module.tool_registry = original


# ---------------------------------------------------------------------------
# Example tools are registered on startup
# ---------------------------------------------------------------------------


def test_example_tools_are_registered() -> None:
    import app.tools.examples.grafana_query  # noqa: F401
    import app.tools.examples.ssh_check_processes  # noqa: F401
    import app.tools.examples.check_data_freshness  # noqa: F401

    assert tool_registry.get("grafana_query") is not None
    assert tool_registry.get("ssh_check_processes") is not None
    assert tool_registry.get("check_data_freshness") is not None


def test_grafana_query_in_all_categories() -> None:
    import app.tools.examples.grafana_query  # noqa: F401
    for cat in ("physical", "data_integrity", "coupling"):
        tools = tool_registry.list_for_category(cat)
        assert any(t.name == "grafana_query" for t in tools)
