from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone

import structlog

from app.core.errors import ToolExecutionError
from app.tools.base import Tool, ToolContext, ToolExecution, ToolInput
from app.tools.registry import tool_registry

log = structlog.get_logger(__name__)


async def execute_tool(
    tool_name: str,
    raw_input: dict,
    ctx: ToolContext,
) -> ToolExecution:
    """Execute a registered tool by name with full lifecycle management.

    Args:
        tool_name: Registered tool name.
        raw_input: Dict that will be validated against the tool's input_model.
        ctx: Runtime context (incident_id, http_client, db_session, etc.)

    Returns:
        ToolExecution with status, output, duration.

    Raises:
        KeyError: If tool_name is not registered.
        ToolExecutionError: On validation failure.
    """
    bound_log = ctx.logger.bind(
        tool=tool_name,
        incident_id=str(ctx.incident_id),
        correlation_id=ctx.correlation_id,
    )

    tool: Tool = tool_registry.get(tool_name)
    started_at = datetime.now(timezone.utc)
    execution_id = uuid.uuid4()

    try:
        typed_input: ToolInput = tool.input_model.model_validate(raw_input)
    except Exception as exc:
        raise ToolExecutionError(tool_name, f"Input validation failed: {exc}") from exc

    bound_log.info("tool_execution_started", execution_id=str(execution_id))

    try:
        async with asyncio.timeout(tool.timeout_seconds):
            output = await tool.execute(typed_input, ctx)

        completed_at = datetime.now(timezone.utc)
        duration_ms = int((completed_at - started_at).total_seconds() * 1000)

        record = ToolExecution(
            id=execution_id,
            incident_id=ctx.incident_id,
            tool_name=tool_name,
            input=raw_input,
            output=output.model_dump(),
            duration_ms=duration_ms,
            status="success",
            started_at=started_at,
            completed_at=completed_at,
        )
        bound_log.info("tool_execution_succeeded", duration_ms=duration_ms)

    except TimeoutError:
        completed_at = datetime.now(timezone.utc)
        duration_ms = int((completed_at - started_at).total_seconds() * 1000)
        record = ToolExecution(
            id=execution_id,
            incident_id=ctx.incident_id,
            tool_name=tool_name,
            input=raw_input,
            duration_ms=duration_ms,
            status="timeout",
            error=f"Timed out after {tool.timeout_seconds}s",
            started_at=started_at,
            completed_at=completed_at,
        )
        bound_log.warning("tool_execution_timeout", timeout_s=tool.timeout_seconds)

    except ToolExecutionError:
        raise

    except Exception as exc:
        completed_at = datetime.now(timezone.utc)
        duration_ms = int((completed_at - started_at).total_seconds() * 1000)
        record = ToolExecution(
            id=execution_id,
            incident_id=ctx.incident_id,
            tool_name=tool_name,
            input=raw_input,
            duration_ms=duration_ms,
            status="error",
            error=str(exc),
            started_at=started_at,
            completed_at=completed_at,
        )
        bound_log.error("tool_execution_failed", error=str(exc), exc_info=True)

    await _persist_execution(record, ctx)
    return record


async def _persist_execution(record: ToolExecution, ctx: ToolContext) -> None:
    """Append execution record to the incident's tool_executions JSONB array."""
    try:
        from sqlalchemy import select, update
        from app.db.models import Incident

        result = await ctx.db_session.execute(
            select(Incident).where(Incident.id == ctx.incident_id)
        )
        incident = result.scalar_one_or_none()
        if incident is None:
            ctx.logger.warning("persist_execution_incident_not_found", incident_id=str(ctx.incident_id))
            return

        executions: list = list(incident.tool_executions or [])
        executions.append(record.model_dump(mode="json"))
        await ctx.db_session.execute(
            update(Incident)
            .where(Incident.id == ctx.incident_id)
            .values(tool_executions=executions)
        )
        await ctx.db_session.flush()
    except Exception as exc:
        ctx.logger.error("persist_execution_failed", error=str(exc))
