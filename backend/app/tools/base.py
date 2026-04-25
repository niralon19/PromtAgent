from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any, ClassVar, Literal

import structlog
from pydantic import BaseModel

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession
    import httpx


class ToolInput(BaseModel):
    """Base class for tool input models."""


class ToolOutput(BaseModel):
    """Base class for tool output models."""


@dataclass
class ToolContext:
    """Runtime context passed to every tool execution."""

    incident_id: uuid.UUID
    correlation_id: str
    logger: Any  # structlog BoundLogger
    http_client: Any  # httpx.AsyncClient
    db_session: Any  # AsyncSession
    config: Any  # Settings


class ToolExecution(BaseModel):
    """Full record of a single tool execution."""

    id: uuid.UUID = field(default_factory=uuid.uuid4)
    incident_id: uuid.UUID
    tool_name: str
    input: dict[str, Any]
    output: dict[str, Any] | None = None
    duration_ms: int = 0
    status: Literal["success", "timeout", "error"] = "success"
    error: str | None = None
    started_at: datetime
    completed_at: datetime | None = None

    model_config = {"arbitrary_types_allowed": True}


class Tool:
    """
    Abstract base class for all diagnostic tools.

    Subclass this and implement `execute`. Register with @register_tool.
    """

    name: ClassVar[str]
    description: ClassVar[str]
    categories: ClassVar[list[str]]
    input_model: ClassVar[type[ToolInput]]
    output_model: ClassVar[type[ToolOutput]]
    timeout_seconds: ClassVar[int] = 30
    safety_level: ClassVar[Literal["read_only", "side_effects"]] = "read_only"

    async def execute(self, input: ToolInput, ctx: ToolContext) -> ToolOutput:
        raise NotImplementedError(
            f"Tool '{self.name}' must implement execute(). "
            "Replace this with your existing diagnostic code."
        )

    def anthropic_schema(self) -> dict[str, Any]:
        """Return Anthropic tool_use compatible schema for this tool."""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_model.model_json_schema(),
        }
