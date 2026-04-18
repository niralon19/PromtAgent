# Data Models Reference

קובץ עזר עם כל ה-Pydantic models/schemas הקריטיים של המערכת. משמש כ-single source 
of truth כשבונים endpoints או UI.

## Core Entities

### GrafanaAlert
```python
class GrafanaAlert(BaseModel):
    alertname: str
    hostname: str
    severity: Literal["info", "warning", "critical"]
    value: float
    labels: dict[str, str]
    annotations: dict[str, str]
    timestamp: datetime
    raw_payload: dict
```

### Incident
```python
class Incident(BaseModel):
    id: UUID
    fingerprint: str
    category: Literal["physical", "data_integrity", "coupling"]
    hostname: str
    status: Literal["triaging", "investigating", "open", "resolved", "false_positive"]
    created_at: datetime
    resolved_at: datetime | None = None
    
    alert: GrafanaAlert
    correlation: CorrelationInfo | None = None
    enrichment: EnrichmentContext | None = None
    tool_executions: list[ToolExecution] = []
    investigation: InvestigationResult | None = None
    ticket: TicketRef | None = None
    resolution: ResolutionData | None = None
    
    embedding: list[float] | None = None
    recurrence_count: int = 0
    tags: list[str] = []
```

### EnrichmentContext
```python
class EnrichmentContext(BaseModel):
    similar_incidents: list[SimilarIncident]
    host_history: HostHistory
    baseline_analysis: BaselineAnalysis
    related_active_incidents: list[UUID]
    recurrence_info: RecurrenceInfo | None
```

### InvestigationResult
```python
class InvestigationResult(BaseModel):
    hypothesis: str
    confidence: int  # 0-100
    confidence_rationale: str
    suggested_action: SuggestedAction
    evidence_chain: list[Evidence]
    alternatives_considered: list[Alternative]
    tools_executed_summary: list[str]
    iterations_used: int
    cost_usd: float
    duration_seconds: float
    checklist_completion: dict[str, bool]
```

### Evidence
```python
class Evidence(BaseModel):
    claim: str
    source_tool: str
    source_output_ref: str  # link to tool_execution
    strength: Literal["weak", "moderate", "strong"]
```

### Alternative
```python
class Alternative(BaseModel):
    hypothesis: str
    why_rejected: str
    evidence_against: list[str]
```

### SuggestedAction
```python
class SuggestedAction(BaseModel):
    action_key: str  # from allowlist
    parameters: dict
    rationale: str
    estimated_risk: Literal["low", "medium", "high"]
    requires_approval: bool
```

### ResolutionData (from Jira feedback)
```python
class ResolutionData(BaseModel):
    resolution_category: str  # from enum table
    actual_resolution_details: str
    was_hypothesis_correct: Literal["yes", "partially", "no"]
    actual_action_taken: str
    resolution_time_minutes: int
    resolved_by: str  # user
    resolved_at: datetime
```

## Tool System

### Tool Protocol
```python
class Tool(Protocol):
    name: ClassVar[str]
    description: ClassVar[str]
    categories: ClassVar[list[str]]
    input_model: ClassVar[type[BaseModel]]
    output_model: ClassVar[type[BaseModel]]
    timeout_seconds: ClassVar[int]
    safety_level: ClassVar[Literal["read_only", "side_effects"]]
    
    async def execute(self, input: BaseModel, ctx: ToolContext) -> BaseModel: ...
```

### ToolExecution
```python
class ToolExecution(BaseModel):
    id: UUID
    incident_id: UUID
    tool_name: str
    input: dict
    output: dict
    duration_ms: int
    status: Literal["success", "timeout", "error"]
    error: str | None
    started_at: datetime
    completed_at: datetime
```

## Metrics & Performance

### ActionMetric
```python
class ActionMetric(BaseModel):
    action_key: str
    total_suggested: int
    total_approved: int
    total_executed: int
    total_hypothesis_correct: int
    total_hypothesis_partially: int
    total_hypothesis_wrong: int
    avg_resolution_time_minutes: float
    streak_days_without_error: int
    last_error_at: datetime | None
    current_tier: int
    last_updated: datetime
```

### HostStatistics
```python
class HostStatistics(BaseModel):
    hostname: str
    total_incidents: int
    incidents_last_30d: int
    incidents_last_7d: int
    most_common_resolution_category: str | None
    avg_resolution_time: float | None
    last_incident_at: datetime | None
    is_recurring_problem: bool
```

### MetricBaseline
```python
class MetricBaseline(BaseModel):
    hostname: str
    metric_name: str
    mean: float
    stddev: float
    p50: float
    p95: float
    p99: float
    sample_count: int
    window_days: int
    computed_at: datetime
```

### BaselineAnalysis
```python
class BaselineAnalysis(BaseModel):
    current_value: float
    z_score: float
    percentile_rank: float
    is_anomaly: bool
    severity_level: Literal["normal", "mild", "moderate", "severe", "extreme"]
    baseline_ref: MetricBaseline
```

## Resolution Categories (enum)

```
hardware_replacement - רכיב חומרה הוחלף
config_change - שינוי configuration
restart_service - restart של שירות
cache_clear - ניקוי cache
scheduled_maintenance - תחזוקה מתוכננת שהוזנחה
false_positive - לא היתה תקלה אמיתית
upstream_issue - בעיה במערכת תלויה
requires_investigation - לא נפתר, דורש חקירה מעמיקה
environmental - בעיה סביבתית (חשמל, קירור)
network_peer - בעיה אצל שכן רשת
software_bug - באג בתוכנה
capacity - בעיית קיבולת (disk full, memory exhaustion)
```

## Categories Detail

### physical
- CPU utilization
- Memory usage / OOM
- Disk space / disk I/O
- Network interface errors/drops
- Temperature
- Hardware failures
- Load average

### data_integrity (הרמטיות)
- Data freshness (last update too old)
- Gaps in time-series data
- Missing expected records
- Pipeline lag
- ETL failures
- Schema drift
- Duplicate detection

### coupling (צימודים)
- BGP peer status
- Link up/down
- Session health (TCP, TLS)
- Protocol mismatches
- Authentication failures between components
- Latency between endpoints
- Route changes
