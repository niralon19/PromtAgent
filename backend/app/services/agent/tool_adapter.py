from __future__ import annotations

from typing import Any

import structlog

from app.tools.base import ToolContext
from app.tools.executor import execute_tool
from app.tools.registry import tool_registry

log = structlog.get_logger(__name__)


def tools_for_anthropic(category: str | None = None) -> list[dict[str, Any]]:
    """Return Anthropic-compatible tool schemas for all (or category-filtered) tools.

    Always includes the `submit_investigation` meta-tool for structured final output.
    """
    if category:
        schemas = tool_registry.schemas_for_category(category)
    else:
        schemas = tool_registry.list_all_schemas_for_llm()

    schemas.append(_submit_investigation_schema())
    return schemas


def _submit_investigation_schema() -> dict[str, Any]:
    return {
        "name": "submit_investigation",
        "description": (
            "Submit your final investigation result. Call this when the diagnostic checklist "
            "is complete or you have exhausted your tool budget. This ends the investigation loop."
        ),
        "input_schema": {
            "type": "object",
            "required": ["hypothesis", "confidence", "confidence_rationale", "suggested_action", "evidence_chain", "alternatives_considered"],
            "properties": {
                "hypothesis": {"type": "string", "description": "Plain-language root cause statement"},
                "confidence": {"type": "integer", "minimum": 0, "maximum": 100},
                "confidence_rationale": {"type": "string"},
                "suggested_action": {
                    "type": "object",
                    "required": ["action_key", "parameters", "rationale"],
                    "properties": {
                        "action_key": {"type": "string"},
                        "parameters": {"type": "object"},
                        "rationale": {"type": "string"},
                    },
                },
                "evidence_chain": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "claim": {"type": "string"},
                            "source_tool": {"type": "string"},
                            "strength": {"type": "string", "enum": ["weak", "moderate", "strong"]},
                        },
                    },
                },
                "alternatives_considered": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "hypothesis": {"type": "string"},
                            "why_rejected": {"type": "string"},
                        },
                    },
                },
                "checklist_notes": {"type": "string"},
            },
        },
    }


async def execute_anthropic_tool_call(
    tool_use_block: Any,
    ctx: ToolContext,
) -> dict[str, Any]:
    """Execute a tool from an Anthropic tool_use response block.

    Args:
        tool_use_block: Anthropic ToolUseBlock with name, id, input.
        ctx: ToolContext for execution.

    Returns:
        Dict with tool result content (or error).
    """
    tool_name: str = tool_use_block.name
    raw_input: dict = tool_use_block.input or {}
    bound_log = ctx.logger.bind(tool=tool_name)

    # submit_investigation is handled by the loop itself, not executed here
    if tool_name == "submit_investigation":
        return {"type": "final_result", "data": raw_input}

    try:
        execution = await execute_tool(tool_name, raw_input, ctx)
        if execution.status == "success":
            return {"output": execution.output, "duration_ms": execution.duration_ms}
        else:
            return {
                "error": execution.error or "Tool execution failed",
                "status": execution.status,
            }
    except KeyError:
        bound_log.warning("tool_not_registered", tool=tool_name)
        return {"error": f"Tool '{tool_name}' is not registered in the registry"}
    except Exception as exc:
        bound_log.error("tool_execution_error", error=str(exc))
        return {"error": str(exc)}
