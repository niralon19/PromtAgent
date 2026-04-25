from __future__ import annotations

from typing import Literal

from pydantic import Field

from app.tools.base import Tool, ToolContext, ToolInput, ToolOutput
from app.tools.registry import register_tool


class ProcessInfo(ToolOutput):
    pid: int
    name: str
    cpu_pct: float
    mem_pct: float
    user: str
    command: str = ""


class SSHCheckProcessesInput(ToolInput):
    hostname: str = Field(description="Target hostname or IP")
    top_n: int = Field(default=10, description="Number of top processes to return", ge=1, le=50)
    sort_by: Literal["cpu", "mem"] = Field(default="cpu", description="Sort processes by CPU or memory")


class SSHCheckProcessesOutput(ToolOutput):
    processes: list[ProcessInfo] = Field(default_factory=list)
    hostname: str
    sampled_at: str


@register_tool
class SSHCheckProcessesTool(Tool):
    """Connect via SSH to a host and return top processes sorted by CPU or memory."""

    name = "ssh_check_processes"
    description = (
        "SSH into a host and return the top N processes sorted by CPU or memory usage. "
        "Use this to identify what is consuming resources on a physical server."
    )
    categories = ["physical"]
    input_model = SSHCheckProcessesInput
    output_model = SSHCheckProcessesOutput
    timeout_seconds = 20
    safety_level = "read_only"

    async def execute(self, input: SSHCheckProcessesInput, ctx: ToolContext) -> SSHCheckProcessesOutput:
        # TODO: Replace with real SSH execution using asyncssh or paramiko
        # Example:
        #   async with asyncssh.connect(input.hostname, ...) as conn:
        #       result = await conn.run(f"ps aux --sort=-{input.sort_by} | head -{input.top_n+1}")
        raise NotImplementedError(
            "SSHCheckProcessesTool: plug in your SSH connection here. "
            "Recommended: asyncssh for async SSH. Use ctx.config for credentials/key paths."
        )
