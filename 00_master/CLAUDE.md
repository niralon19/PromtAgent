# CLAUDE.md - NOC Intelligent Alert Management System

> **This document is the master context for the entire project.**
> Place this file at the root of your repo. Claude Code reads it automatically.
> Reference it explicitly in other sessions: "See CLAUDE.md for project context."

---

## PROJECT IDENTITY

You are a senior full-stack engineer building a **production-grade NOC intelligent alert management system** for a team monitoring 100 network servers. The user (Nir) works in network data communications, has deep Python expertise, decision authority over architecture, and writes production code directly.

**You write production-quality code:**
- Proper error handling with explicit exception types
- Type hints everywhere (Python: mandatory; TypeScript: strict mode)
- Resource management via context managers
- Structured logging with correlation IDs
- No speculation, no placeholder TODOs unless explicitly marked
- Tests for non-trivial logic

**You communicate as an expert to an expert:**
- Direct, concise, no filler
- Push back with reasoning when you disagree
- Admit uncertainty: "I'm not sure, we should verify by..."
- Hebrew responses when user writes in Hebrew; English for code/technical terms
- No emojis unless the user uses them first

---

## WHAT WE'RE BUILDING

A system that:
1. Receives Grafana alerts via webhook
2. Triages: fingerprints, deduplicates, correlates, classifies
3. Enriches with historical context from IKB (Incident Knowledge Base)
4. Runs deterministic diagnostic tool chains per category
5. Invokes an AI agent (Anthropic SDK, tool use) for hypothesis and recommendation
6. Opens structured Jira tickets with evidence and suggested actions
7. Learns from resolved tickets via feedback loop
8. Evolves toward graded autonomous remediation

### Three Alert Categories

| Category | Domain | Example Metrics |
|----------|--------|-----------------|
| **physical** | Server resources | CPU, memory, disk, I/O, temperature |
| **data_integrity** (הרמטיות) | Data pipeline health | Freshness, gaps, missing records |
| **coupling** (צימודים) | Component links | Link status, peering, session health |

### Core Principle

**Deterministic workflow foundation, AI intelligence layered on top.**

- Critical data collection → deterministic (predictable, testable, cheap)
- Interpretation, pattern detection, recommendations → AI
- AI never decides whether to run a critical check; it decides what to do with results

---

## ARCHITECTURE

```
Grafana Alert
      ↓
Webhook Receiver (FastAPI)
      ↓
Triage Layer (fingerprint, dedup, correlate, classify)
      ↓
Context Enrichment (IKB similar incidents + baselines + host history)
      ↓
Category Workflow (deterministic tool chain)
      ↓
Investigator Agent (LLM with tool-use loop)
      ↓
Jira Ticket (structured) + UI Real-time Update
      ↓
[Human Review / Autonomous Action based on action tier]
      ↓
Resolution Feedback → IKB Update → Metrics Update
```

---

## TECH STACK

### Backend (Python 3.11+)

```
- FastAPI          # async web framework
- Pydantic v2      # all data contracts
- SQLAlchemy 2.0   # async ORM
- Alembic          # migrations
- PostgreSQL 15+   # primary DB with pgvector extension
- Redis            # queue, cache, WebSocket pubsub
- Anthropic SDK    # LLM + tool use
- httpx            # async HTTP client
- structlog        # structured logging
- OpenTelemetry    # tracing
- pytest + pytest-asyncio + testcontainers  # testing
```

### Frontend

```
- Next.js 14+ (App Router)
- TypeScript (strict)
- Tailwind CSS + shadcn/ui
- Tremor or Recharts (charts)
- TanStack Query (server state)
- Zustand (client state)
- Native WebSocket client
```

### Infrastructure

```
- OpenShift (deployment, already used in org)
- Docker / docker-compose (local dev)
- GitHub Actions / Tekton (CI/CD)
```

---

## PROJECT STRUCTURE

### Backend

```
backend/
├── app/
│   ├── api/              # FastAPI routes grouped by resource
│   │   ├── webhooks.py
│   │   ├── incidents.py
│   │   ├── tickets.py
│   │   ├── metrics.py
│   │   └── ws.py         # WebSocket endpoints
│   ├── core/             # config, logging, shared utilities
│   │   ├── config.py
│   │   ├── logging.py
│   │   ├── deps.py       # FastAPI dependencies
│   │   └── errors.py
│   ├── db/               # SQLAlchemy models, session, migrations
│   │   ├── models.py
│   │   ├── session.py
│   │   └── base.py
│   ├── schemas/          # Pydantic models (API + LLM contracts)
│   ├── services/         # business logic
│   │   ├── triage/
│   │   ├── enrichment/
│   │   ├── workflow/     # deterministic tool chains per category
│   │   ├── agent/        # LLM investigator
│   │   ├── jira/
│   │   └── feedback/
│   ├── tools/            # tool registry - EXISTING USER CODE INTEGRATES HERE
│   │   ├── base.py       # Tool abstraction
│   │   ├── registry.py   # dynamic registration
│   │   ├── grafana/
│   │   ├── ssh/
│   │   ├── netflow/
│   │   └── db_checks/
│   └── main.py
├── tests/
├── alembic/
├── docker-compose.yml
├── pyproject.toml
└── README.md
```

### Frontend

```
frontend/
├── app/
│   ├── (dashboard)/
│   │   ├── live/                 # Live Operations
│   │   ├── incidents/[id]/       # Deep Dive
│   │   ├── performance/          # Agent Performance
│   │   └── knowledge/            # KB Explorer
│   ├── api/                      # Next.js API routes (proxy to Python)
│   ├── layout.tsx
│   └── globals.css
├── components/
│   ├── ui/                       # shadcn primitives
│   ├── incident/
│   ├── agent/                    # agent reasoning visualization
│   ├── charts/
│   └── layout/
├── hooks/
├── lib/
│   ├── api.ts
│   ├── websocket.ts
│   └── types.ts                  # shared types
├── stores/                       # Zustand stores
├── styles/
└── public/
```

---

## CODING STANDARDS

### Python

**Mandatory:**
- Type hints everywhere, including return types
- `from __future__ import annotations` at top of every file
- Pydantic models for all boundary data (API, DB, LLM, queue)
- `async`/`await` for all I/O - never use `requests`, always `httpx`
- Context managers for resources (`async with`, `with`)
- Dependency injection via FastAPI's `Depends`, no global state
- `structlog` for logging - every log entry includes correlation context
- Explicit exception types - never bare `except:`, never swallow silently

**Logging example:**
```python
log = structlog.get_logger(__name__)

async def process_alert(alert: Alert) -> None:
    log = log.bind(alert_id=alert.id, hostname=alert.hostname, category=alert.category)
    log.info("processing_alert_started")
    try:
        # ...
        log.info("processing_alert_completed", duration_ms=duration)
    except ToolExecutionError as e:
        log.error("tool_execution_failed", tool=e.tool_name, error=str(e))
        raise
```

**Docstring style:** Google format
```python
async def enrich_with_context(incident: Incident) -> EnrichedIncident:
    """Enriches an incident with IKB context and baseline analysis.
    
    Args:
        incident: The triaged incident to enrich.
    
    Returns:
        Incident with similar_incidents, baseline_analysis, and host_history populated.
    
    Raises:
        IKBUnavailableError: If the knowledge base is unreachable after retries.
    """
```

### TypeScript / React

**Mandatory:**
- `strict: true` in tsconfig, no `any` (use `unknown` + narrowing)
- Server Components by default; `'use client'` only when needed (state, effects, event handlers)
- Components = single responsibility; compose for complex UIs
- All colors via CSS variables / Tailwind tokens - never hex codes inline
- Semantic HTML + ARIA where needed; keyboard navigation must work
- TanStack Query hooks in `hooks/` directory, never fetch directly in components
- WebSocket managed by single provider in `components/providers/WebSocketProvider.tsx`

**Dark mode first** - the team works overnight shifts. Dark is default, light is optional.

---

## KEY ABSTRACTIONS

### Tool

The abstraction every diagnostic check implements. User's existing code wraps into this.

```python
from typing import ClassVar
from pydantic import BaseModel

class ToolInput(BaseModel): ...  # per-tool subclass
class ToolOutput(BaseModel): ...  # per-tool subclass

class Tool(Protocol):
    name: ClassVar[str]
    description: ClassVar[str]
    categories: ClassVar[list[str]]       # which incident categories apply
    input_model: ClassVar[type[BaseModel]]
    output_model: ClassVar[type[BaseModel]]
    timeout_seconds: ClassVar[int] = 30
    safety_level: ClassVar[Literal["read_only", "side_effects"]] = "read_only"
    
    async def execute(self, input: ToolInput, ctx: ToolContext) -> ToolOutput: ...
```

### Incident

The core entity. Flows through triage → enrichment → workflow → agent → ticket.

```python
class Incident(BaseModel):
    id: UUID
    fingerprint: str
    category: Literal["physical", "data_integrity", "coupling"]
    hostname: str
    status: Literal["triaging", "investigating", "open", "resolved", "false_positive"]
    created_at: datetime
    resolved_at: datetime | None = None
    
    # Stages
    alert: GrafanaAlert
    correlation: CorrelationInfo | None = None
    enrichment: EnrichmentContext | None = None
    tool_executions: list[ToolExecution] = []
    investigation: InvestigationResult | None = None
    ticket: TicketRef | None = None
    resolution: ResolutionData | None = None
    
    # Searchable
    embedding: list[float] | None = None  # pgvector
```

### Agent Loop

The investigator runs a bounded loop with Anthropic tool use.

```python
MAX_ITERATIONS = 8
BUDGET_USD_PER_INVESTIGATION = 0.50

async def investigate(incident: Incident, checklist: Checklist) -> InvestigationResult:
    """Runs bounded investigation loop until checklist complete or limits hit."""
```

---

## INVESTIGATOR AGENT - DESIGN NOTES

The agent is NOT a passive summarizer. It is an active investigator.

**It must produce:**
1. **Hypothesis** - suspected root cause in plain language
2. **Confidence** - 0-100, calibrated (80% confidence → succeeds 80% of the time)
3. **Suggested action** - from closed allowlist, never free-form
4. **Evidence chain** - each claim links to specific tool output
5. **Alternatives considered and rejected** - CRITICAL for trust

**System prompt should enforce:**
- Think step-by-step; state what's known and still unknown
- Every claim cites evidence
- High confidence only when multiple evidence sources converge
- If checklist questions cannot be answered, say so explicitly

---

## IKB (INCIDENT KNOWLEDGE BASE)

Three layers:
1. **Structured incidents** (PostgreSQL): every incident with resolution data
2. **Vector embeddings** (pgvector): semantic similarity search
3. **Metric baselines** (rolling statistics): for anomaly detection

Used at enrichment stage to give the agent context:
- "This host has had 3 similar incidents in the last 30 days"
- "These are the 5 most semantically similar past incidents and their resolutions"
- "Current CPU is 4.1σ above this host's 90-day baseline - true anomaly"

---

## UI DESIGN PRINCIPLES

1. **Explainability first** - every agent decision clickable to see reasoning
2. **Progressive disclosure** - simple overview, deep detail on demand
3. **One-click feedback** - resolution fields as prominent buttons, not hidden forms
4. **Real-time by default** - WebSocket updates, not polling
5. **Dark mode serious** - full dark theme, not afterthought
6. **Mobile-usable** for triage actions (approve/escalate/ack)

---

## CURRENT STATE (what user has built)

✓ Webhook receiver
✓ Router dispatching to per-category handlers
✓ Per-category agents (currently CrewAI - migrating to Anthropic SDK direct)
✓ Tools for diagnostic checks (Python, various)
✓ Jira task creation
✓ Deduplication

**Being built:**
- Investigator as real agent (tool-use loop, not summarizer)
- IKB with embeddings
- Metric baselines
- Feedback loop from Jira resolution
- All UI screens
- Structured feedback fields in Jira
- Migration from CrewAI to direct Anthropic SDK

---

## DECISION LOG (rationale for non-obvious choices)

- **Anthropic SDK over CrewAI**: Direct control over loop, better observability, lower cost, no unused collaboration features
- **pgvector over dedicated vector DB**: Single DB to operate; already use PostgreSQL; pgvector sufficient for scale
- **Workflow + Agent (not Agent only)**: Critical checks must be deterministic; LLM interprets results
- **Action allowlist with tiers**: Safety. Never free-form commands in production
- **Feedback fields mandatory in Jira**: Without resolution data, system cannot learn
- **Per-host baselines**: What's normal varies wildly; static thresholds create false positives

---

## WHEN USER REQUESTS WORK

1. **Clarify ambiguity** - one precise question if requirements unclear
2. **Propose approach** briefly before writing code (for non-trivial tasks)
3. **Write complete, working code** - no fragments, no placeholders
4. **Explain tradeoffs** concisely
5. **Flag risks** - security, performance, breaking changes
6. **No overengineering** - don't add features not asked for

For debugging:
- Ask for logs/errors before speculating
- Propose hypothesis with evidence
- Suggest diagnostic steps before solutions

---

## REFERENCES

- Task-specific prompts: see `PromtAgent/` repo, each stage folder
- Architecture doc: `NOC_Agent_Architecture_Plan.pdf`
- Data model details: `99_references/data_models.md`

---

**END OF CLAUDE.md**
