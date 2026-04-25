# Tool Registry — Migration Guide

Every diagnostic check in the system must be wrapped in a `Tool` subclass and registered.
This gives the agent a consistent interface, timeout enforcement, structured logging, and DB persistence.

## Registering a New Tool

```python
from app.tools.base import Tool, ToolInput, ToolOutput
from app.tools.registry import register_tool
from pydantic import Field

class MyCheckInput(ToolInput):
    hostname: str = Field(description="Target host")
    threshold: float = Field(default=90.0, description="Alert threshold %")

class MyCheckOutput(ToolOutput):
    current_value: float
    exceeded: bool
    message: str

@register_tool
class MyCheckTool(Tool):
    name = "my_check"                        # unique, snake_case
    description = "One sentence the LLM reads to decide whether to call this tool."
    categories = ["physical"]               # ["physical"] | ["data_integrity"] | ["coupling"] | any combo
    input_model = MyCheckInput
    output_model = MyCheckOutput
    timeout_seconds = 15
    safety_level = "read_only"              # "read_only" | "side_effects"

    async def execute(self, input: MyCheckInput, ctx: ToolContext) -> MyCheckOutput:
        # your code here
        result = await some_async_check(input.hostname, ctx.http_client)
        return MyCheckOutput(
            current_value=result.value,
            exceeded=result.value > input.threshold,
            message=f"Value is {result.value}",
        )
```

Then import the module in `app/main.py` so it registers at startup:
```python
import app.tools.my_module  # noqa: F401
```

## Migrating Existing Code

Checklist for wrapping an existing function:

1. **Create `Input` model** — list every parameter your function takes
2. **Create `Output` model** — list every field your function returns
3. **Write `execute()`** — call your existing code, return the output model
4. **Pick `categories`** — which alert categories can this tool help with?
5. **Set `timeout_seconds`** — be conservative (30s default)
6. **Set `safety_level`** — `"side_effects"` if the tool modifies state
7. **Register with `@register_tool`**
8. **Import in `main.py`**
9. **Write a test** — mock external calls, test input validation, test output shape

## Example: migrating a plain function

**Before:**
```python
async def check_bgp_peers(router_ip: str, expected_peers: list[str]) -> dict:
    ...
```

**After:**
```python
class BGPPeerCheckInput(ToolInput):
    router_ip: str
    expected_peers: list[str]

class BGPPeerCheckOutput(ToolOutput):
    up_peers: list[str]
    down_peers: list[str]
    all_up: bool

@register_tool
class BGPPeerCheckTool(Tool):
    name = "bgp_peer_check"
    description = "Check BGP peer status on a router. Returns up/down peers."
    categories = ["coupling"]
    input_model = BGPPeerCheckInput
    output_model = BGPPeerCheckOutput
    timeout_seconds = 20
    safety_level = "read_only"

    async def execute(self, input: BGPPeerCheckInput, ctx: ToolContext) -> BGPPeerCheckOutput:
        result = await check_bgp_peers(input.router_ip, input.expected_peers)
        return BGPPeerCheckOutput(**result)
```

## ToolContext contents

| Field | Type | Use |
|-------|------|-----|
| `incident_id` | UUID | For logging/correlating |
| `correlation_id` | str | Request-level correlation |
| `logger` | structlog BoundLogger | Pre-bound with incident context |
| `http_client` | httpx.AsyncClient | For HTTP calls to Grafana, APIs |
| `db_session` | AsyncSession | For analytics DB queries |
| `config` | Settings | For credentials, URLs |
