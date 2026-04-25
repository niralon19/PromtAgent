from __future__ import annotations

from typing import Any

from pydantic import Field

from app.tools.base import Tool, ToolContext, ToolInput, ToolOutput
from app.tools.registry import register_tool


class GrafanaQueryInput(ToolInput):
    datasource_uid: str = Field(description="Grafana datasource UID")
    query: str = Field(description="PromQL or SQL query expression")
    time_from: str = Field(default="now-1h", description="Start time (Grafana relative or ISO)")
    time_to: str = Field(default="now", description="End time")
    max_data_points: int = Field(default=500, description="Max data points to return")


class GrafanaQueryOutput(ToolOutput):
    series: list[dict[str, Any]] = Field(description="List of {name, timestamps, values}")
    meta: dict[str, Any] = Field(default_factory=dict, description="Query metadata")
    row_count: int = 0


@register_tool
class GrafanaQueryTool(Tool):
    """Query a Grafana datasource (PromQL or SQL) and return time series data."""

    name = "grafana_query"
    description = (
        "Query a Grafana datasource using PromQL or SQL. "
        "Use this to retrieve metric time series for a specific host or service. "
        "Returns data points with timestamps and values."
    )
    categories = ["physical", "data_integrity", "coupling"]
    input_model = GrafanaQueryInput
    output_model = GrafanaQueryOutput
    timeout_seconds = 30
    safety_level = "read_only"

    async def execute(self, input: GrafanaQueryInput, ctx: ToolContext) -> GrafanaQueryOutput:
        # TODO: Replace with real Grafana API call using ctx.http_client
        # Example:
        #   resp = await ctx.http_client.post(
        #       f"{ctx.config.grafana_url}/api/ds/query",
        #       headers={"Authorization": f"Bearer {ctx.config.grafana_token}"},
        #       json={...}
        #   )
        raise NotImplementedError(
            "GrafanaQueryTool: plug in your Grafana API call here. "
            "Use ctx.http_client (httpx.AsyncClient) and ctx.config for credentials."
        )
