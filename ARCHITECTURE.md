# PromtAgent — Architecture & Deployment Guide

## Overview

PromtAgent is a production-grade NOC (Network Operations Center) automation system.
It ingests alerts from Grafana, triages them deterministically, investigates via AI agents,
creates Jira tickets, and evolves toward autonomous remediation through a feedback loop.

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          External Services                               │
│   Grafana (alerts) │ Jira (tickets) │ Anthropic API (LLM)               │
└────────┬───────────┴───────┬─────────┴──────────┬────────────────────────┘
         │ Webhook            │ REST API            │ SDK
         ▼                   │                     │
┌────────────────────────────────────────────────────────────────────────┐
│                         Backend  (FastAPI / Python 3.11+)               │
│                                                                         │
│  ┌───────────────┐   ┌──────────────────┐   ┌──────────────────────┐   │
│  │  API Routers  │   │  Triage Pipeline │   │  Investigator Agent  │   │
│  │ /webhooks     │──▶│  1. Fingerprint  │──▶│  Tool-use loop       │   │
│  │ /incidents    │   │  2. Dedup        │   │  (Anthropic SDK)     │   │
│  │ /knowledge    │   │  3. Correlate    │   │  Tool Registry       │   │
│  │ /autonomy     │   │  4. Classify     │   └──────────┬───────────┘   │
│  │ /feedback     │   └──────────────────┘              │               │
│  │ /metrics      │   ┌──────────────────┐   ┌──────────▼───────────┐   │
│  │ /ws           │   │  IKB Service     │   │  Autonomy Executor   │   │
│  └───────────────┘   │  Embeddings      │   │  Shadow Mode         │   │
│                      │  Similarity      │   │  Circuit Breaker     │   │
│                      │  Baselines       │   │  Rollback            │   │
│                      └──────────────────┘   └──────────────────────┘   │
│                                                                         │
│  ┌───────────────────────┐   ┌──────────────────────────────────────┐  │
│  │  Jira Integration     │   │  Feedback & Learning                 │  │
│  │  Ticket creation      │   │  Pattern detection                   │  │
│  │  Sync handler         │   │  Recurrence detection                │  │
│  │  Polling fallback     │   │  Metrics / quality scoring           │  │
│  └───────────────────────┘   └──────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
         │ SQL (async)               │ Redis pub/sub + cache
         ▼                           ▼
┌──────────────────┐     ┌─────────────────────────┐
│  PostgreSQL 15+  │     │  Redis 7                │
│  pgvector ext.   │     │  Queue + WebSocket bus  │
└──────────────────┘     └─────────────────────────┘
         ▲
         │ HTTP / WebSocket
┌─────────────────────────────────────────────────────┐
│               Frontend  (Next.js 14 / TypeScript)   │
│                                                     │
│  ┌─────────────────┐   ┌──────────────────────────┐ │
│  │  Live Incidents │   │  Incident Deep Dive      │ │
│  │  /live          │   │  /incidents/[id]         │ │
│  └─────────────────┘   └──────────────────────────┘ │
│  ┌─────────────────┐   ┌──────────────────────────┐ │
│  │  Knowledge Base │   │  Autonomy Dashboard      │ │
│  │  /knowledge     │   │  /autonomy               │ │
│  └─────────────────┘   └──────────────────────────┘ │
│  ┌─────────────────┐                                │
│  │  Performance    │   Zustand + React Query        │
│  │  /performance   │   Radix UI + Tailwind          │
│  └─────────────────┘                                │
└─────────────────────────────────────────────────────┘
```

---

## Data Flow — Alert to Resolution

```
1. Grafana fires webhook  ──▶  POST /api/v1/webhooks
                                      │
2. Triage Pipeline                    ▼
   ├── Fingerprint (hash of labels)
   ├── Dedup (Redis TTL check)
   ├── Correlation (group related alerts → Incident)
   └── Classify  (physical / data_integrity / coupling)
                                      │
3. Context Enrichment                 ▼
   ├── IKB similarity search (pgvector)
   ├── Host baselines
   └── Historical patterns
                                      │
4. Investigator Agent                 ▼
   ├── Tool-use loop (Anthropic claude-sonnet)
   ├── Runs tools from Tool Registry (Grafana, SSH, etc.)
   └── Produces structured evidence + recommended action
                                      │
5. Jira Ticket                        ▼
   └── Created with full evidence, severity, action tier
                                      │
6. UI Real-time Update                ▼
   └── WebSocket broadcast → Live Incidents page
                                      │
7. Resolution Feedback                ▼
   ├── Operator resolves + submits feedback
   ├── IKB updated with new resolution pattern
   ├── Metrics updated
   └── Autonomy tier may be promoted
```

---

## Backend Structure

```
backend/
├── app/
│   ├── main.py                  # FastAPI app, lifespan, middleware, routers
│   ├── config.py                # Pydantic settings (env vars)
│   ├── database.py              # SQLAlchemy async engine + session factory
│   ├── api/v1/                  # Route handlers
│   │   ├── webhooks.py
│   │   ├── incidents.py
│   │   ├── feedback.py
│   │   ├── websocket.py
│   │   ├── metrics.py
│   │   ├── knowledge.py
│   │   └── autonomy.py
│   ├── models/                  # SQLAlchemy ORM models
│   ├── schemas/                 # Pydantic request/response schemas
│   ├── services/
│   │   ├── triage/              # Fingerprint, dedup, correlation, classifier
│   │   ├── ikb/                 # Incident Knowledge Base + embeddings
│   │   ├── agent/               # Investigator, executor, prompts, parser
│   │   ├── autonomy/            # Tier manager, shadow mode, circuit breaker
│   │   ├── jira/                # Client, ticket creator, sync, templates
│   │   └── feedback/            # Orchestrator, pattern detector, metrics
│   └── tools/
│       ├── base.py              # Abstract Tool base class
│       ├── registry.py          # Central tool registry
│       ├── executor.py          # Tool execution with timeout/error handling
│       └── examples/            # Grafana, SSH, data freshness tools
├── alembic/                     # DB migrations (5 migrations)
├── config/
│   ├── classification_rules.yaml
│   └── actions.yaml             # 11 action tiers
├── tests/
├── docker-compose.yml           # PostgreSQL 15 (pgvector) + Redis 7
├── pyproject.toml
└── .env.example
```

---

## Frontend Structure

```
frontend/
├── app/
│   ├── layout.tsx               # Root layout: QueryProvider + WebSocketProvider + ThemeProvider
│   └── (dashboard)/
│       ├── live/                # Live Incidents list (WebSocket real-time)
│       ├── incidents/[id]/      # Incident Deep Dive
│       ├── knowledge/           # IKB search + filters
│       ├── performance/         # Quality & operational metrics
│       └── autonomy/            # Tier management + kill switch
├── components/
│   ├── incidents/               # IncidentRow, Header, StatsBar, FilterBar, ActionBar
│   ├── analysis/                # AgentReasoning, AnalysisPanel, IKBContextPanel
│   └── common/                  # SeverityBadge, CategoryBadge, ConfidenceBar, RelativeTime
├── lib/
│   ├── api.ts                   # Centralized fetch client → /api/v1
│   ├── store.ts                 # Zustand state stores
│   └── websocket.ts             # WebSocket client + provider
├── next.config.js               # API rewrites: /api/v1 → localhost:8000
├── tailwind.config.ts
└── package.json
```

---

## Key Design Principles

| Principle | Implementation |
|---|---|
| Deterministic first, AI second | Core triage is rule-based; AI adds interpretation on top |
| Async-first | All Python uses `async/await`, asyncpg, SQLAlchemy async |
| Structured logging | structlog + X-Request-ID correlation through all layers |
| Shadow before autonomy | Actions run in shadow mode, validated before live execution |
| Feedback loop | Resolution data updates IKB + metrics + autonomy tier |
| Tool registry pattern | Tools registered via decorator, Anthropic schema auto-generated |

---

## Alert Classification

Defined in `config/classification_rules.yaml`:

| Category | Signals |
|---|---|
| `physical` | CPU, memory, disk, I/O, load, temperature, hardware |
| `data_integrity` | Freshness, gaps, pipeline, ETL lag, schema drift |
| `coupling` | BGP, peers, links, sessions, latency, tunnels, OSPF, ISIS |

---

## Autonomy Tiers

Defined in `config/actions.yaml` — 11 tiers from least to most impactful:

1. `NOTE_IN_TICKET` — Add analysis note to Jira
2. `ALERT_OWNER` — Ping alert owner in ticket
3. `CREATE_INCIDENT_CHANNEL` — Create communication channel
4. `SILENCE_ALERT` — Suppress alert in Grafana
5. `SCALE_OUT_REPLICAS` — Add replicas
6. `BOUNCE_SERVICE` — Restart service
7. `ROLLBACK_DEPLOYMENT` — Revert last deploy
8. `FLUSH_CACHE` — Clear caches
9. `FAILOVER_TRAFFIC` — Reroute traffic
10. `QUARANTINE_HOST` — Isolate host
11. `REBOOT_HOST` — Full host reboot

---

## Environment Variables

Create `backend/.env` based on `backend/.env.example`:

```dotenv
# Database
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/promt_agent
DATABASE_POOL_SIZE=10
DATABASE_MAX_OVERFLOW=20

# Redis
REDIS_URL=redis://localhost:6379

# CORS
CORS_ORIGINS=["http://localhost:3000"]

# LLM
ANTHROPIC_API_KEY=sk-ant-...

# Jira
JIRA_URL=https://your-org.atlassian.net
JIRA_USER=your@email.com
JIRA_TOKEN=your-jira-api-token
JIRA_PROJECT_KEY=NOC

# Grafana
GRAFANA_WEBHOOK_SECRET=your-secret
```

---

## Local Development — Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- Docker + Docker Compose

### 1. Infrastructure (PostgreSQL + Redis)

```bash
cd backend
docker-compose up -d
```

Starts:
- PostgreSQL 15 with pgvector on port `5432`
- Redis 7 on port `6379`

### 2. Backend

```bash
cd backend

# Copy and fill environment
cp .env.example .env
# Edit .env with your ANTHROPIC_API_KEY, JIRA credentials, etc.

# Install dependencies
pip install -e ".[dev]"

# Run database migrations
python -m alembic upgrade head

# Start the server
uvicorn app.main:app --reload --port 8000
```

Backend runs at: `http://localhost:8000`
API docs (Swagger): `http://localhost:8000/docs`
Health check: `http://localhost:8000/health`

### 3. Frontend

```bash
cd frontend

npm install
npm run dev
```

Frontend runs at: `http://localhost:3000`

---

## Testing

```bash
cd backend

# Unit tests
pytest tests/ -v

# With coverage
pytest tests/ --cov=app --cov-report=html

# Integration tests (requires Docker for testcontainers)
pytest tests/integration/ -v
```

---

## Production Deployment

### Docker Compose (Recommended for Single-Server)

Create `docker-compose.prod.yml`:

```yaml
version: "3.9"

services:
  db:
    image: pgvector/pgvector:pg15
    environment:
      POSTGRES_DB: promt_agent
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - pgdata:/var/lib/postgresql/data
    restart: always

  redis:
    image: redis:7-alpine
    restart: always

  backend:
    build: ./backend
    env_file: ./backend/.env
    ports:
      - "8000:8000"
    depends_on:
      - db
      - redis
    restart: always
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4

  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    environment:
      NEXT_PUBLIC_API_URL: http://backend:8000
    depends_on:
      - backend
    restart: always

volumes:
  pgdata:
```

Run:
```bash
docker-compose -f docker-compose.prod.yml up -d
```

### Backend Dockerfile (add to `backend/Dockerfile`)

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY pyproject.toml .
RUN pip install -e ".[prod]"
COPY . .
RUN alembic upgrade head
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

### Frontend Dockerfile (add to `frontend/Dockerfile`)

```dockerfile
FROM node:18-alpine AS builder
WORKDIR /app
COPY package*.json .
RUN npm ci
COPY . .
RUN npm run build

FROM node:18-alpine AS runner
WORKDIR /app
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
EXPOSE 3000
CMD ["node", "server.js"]
```

---

## Service Communication Map

```
Frontend (3000)
    │
    ├── HTTP REST → Backend API (8000)  [via Next.js rewrites]
    └── WebSocket → /api/v1/ws (8000)

Backend (8000)
    ├── PostgreSQL (5432)               [SQLAlchemy async]
    ├── Redis (6379)                    [aioredis — cache + pub/sub]
    ├── Anthropic API (external HTTPS)  [anthropic SDK]
    ├── Jira API (external HTTPS)       [httpx async client]
    └── Grafana API (external HTTPS)    [tool calls]
```

---

## Monitoring & Observability

| Endpoint | Purpose |
|---|---|
| `GET /health` | Liveness check — returns `{"status": "ok"}` |
| `GET /api/v1/metrics` | Operational metrics (triaged, resolved, MTTR, accuracy) |
| `GET /api/v1/metrics/quality` | Agent quality scores per category |

Logs are structured JSON via `structlog` with `request_id` correlation on every line.

---

## Security Notes

- Grafana webhook endpoint validates `GRAFANA_WEBHOOK_SECRET` via HMAC
- Jira token is stored only in environment variables, never in DB
- CORS is restricted to configured `CORS_ORIGINS`
- All DB queries use parameterized statements via SQLAlchemy ORM (no raw SQL injection risk)
- Autonomy actions above tier 5 require explicit promotion through shadow-mode validation
