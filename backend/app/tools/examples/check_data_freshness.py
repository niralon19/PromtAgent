from __future__ import annotations

from datetime import datetime

from pydantic import Field

from app.tools.base import Tool, ToolContext, ToolInput, ToolOutput
from app.tools.registry import register_tool


class TimeGap(ToolOutput):
    start: str
    end: str
    duration_minutes: float


class CheckDataFreshnessInput(ToolInput):
    table_name: str = Field(description="Fully qualified table name (schema.table)")
    timestamp_column: str = Field(description="Name of the timestamp column to inspect")
    threshold_minutes: int = Field(
        default=15,
        description="Alert if last record is older than this many minutes",
    )
    gap_detection_minutes: int = Field(
        default=60,
        description="Scan this many minutes back for internal gaps",
    )


class CheckDataFreshnessOutput(ToolOutput):
    last_record_ts: str | None = Field(description="ISO timestamp of the most recent record")
    minutes_since_last: float | None = Field(description="Minutes since last record")
    is_fresh: bool = Field(description="True if last record is within threshold")
    gap_ranges: list[TimeGap] = Field(default_factory=list, description="Detected data gaps")
    row_count_last_hour: int = 0


@register_tool
class CheckDataFreshnessTool(Tool):
    """Check data freshness and detect gaps in a time-series DB table."""

    name = "check_data_freshness"
    description = (
        "Check when data was last written to a database table and detect time gaps. "
        "Use this to diagnose data_integrity incidents: stale data, pipeline stalls, ETL failures."
    )
    categories = ["data_integrity"]
    input_model = CheckDataFreshnessInput
    output_model = CheckDataFreshnessOutput
    timeout_seconds = 15
    safety_level = "read_only"

    async def execute(self, input: CheckDataFreshnessInput, ctx: ToolContext) -> CheckDataFreshnessOutput:
        # TODO: Replace with real DB query using ctx.db_session or a dedicated
        # analytics DB session from ctx.config.
        # Example query:
        #   SELECT MAX({timestamp_column}) as last_ts,
        #          COUNT(*) FILTER (WHERE {ts_col} > NOW() - INTERVAL '1 hour') as cnt
        #   FROM {table_name}
        raise NotImplementedError(
            "CheckDataFreshnessTool: plug in your DB query here. "
            "Use ctx.db_session for the analytics DB connection."
        )
