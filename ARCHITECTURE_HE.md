# PromtAgent — מסמך ארכיטקטורה ופריסה

## סקירה כללית

PromtAgent הוא מערכת אוטומציה לחדר בקרה תפעולי (NOC) ברמת פרודקשן.
המערכת קולטת התראות מ-Grafana, מבצעת triage דטרמיניסטי, חוקרת באמצעות סוכני AI,
יוצרת כרטיסי Jira, ומתפתחת לקראת פעולה אוטונומית דרך לולאת משוב.

---

## ארכיטקטורת המערכת

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          שירותים חיצוניים                               │
│   Grafana (התראות) │ Jira (כרטיסים) │ Anthropic API (מודל שפה)         │
└────────┬───────────┴───────┬─────────┴──────────┬────────────────────────┘
         │ Webhook            │ REST API            │ SDK
         ▼                   │                     │
┌────────────────────────────────────────────────────────────────────────┐
│                         Backend  (FastAPI / Python 3.11+)               │
│                                                                         │
│  ┌───────────────┐   ┌──────────────────┐   ┌──────────────────────┐   │
│  │  נתיבי API   │   │  צינור Triage    │   │  סוכן חקירה          │   │
│  │ /webhooks     │──▶│  1. טביעת אצבע  │──▶│  לולאת שימוש בכלים  │   │
│  │ /incidents    │   │  2. כפילויות    │   │  (Anthropic SDK)     │   │
│  │ /knowledge    │   │  3. קורלציה     │   │  רישום כלים          │   │
│  │ /autonomy     │   │  4. סיווג       │   └──────────┬───────────┘   │
│  │ /feedback     │   └──────────────────┘              │               │
│  │ /metrics      │   ┌──────────────────┐   ┌──────────▼───────────┐   │
│  │ /ws           │   │  שירות IKB      │   │  מנוע אוטונומיה      │   │
│  └───────────────┘   │  Embeddings      │   │  מצב צל             │   │
│                      │  דמיון סמנטי    │   │  מפסק זרם            │   │
│                      │  בסיסי ייחוס   │   │  Rollback            │   │
│                      └──────────────────┘   └──────────────────────┘   │
│                                                                         │
│  ┌───────────────────────┐   ┌──────────────────────────────────────┐  │
│  │  אינטגרציית Jira     │   │  משוב ולמידה                        │  │
│  │  יצירת כרטיסים       │   │  זיהוי דפוסים                       │  │
│  │  סנכרון              │   │  זיהוי חזרתיות                      │  │
│  │  Polling fallback     │   │  מדדים / ניקוד איכות               │  │
│  └───────────────────────┘   └──────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
         │ SQL (אסינכרוני)           │ Redis pub/sub + cache
         ▼                           ▼
┌──────────────────┐     ┌─────────────────────────┐
│  PostgreSQL 15+  │     │  Redis 7                │
│  תוסף pgvector  │     │  תור + WebSocket bus     │
└──────────────────┘     └─────────────────────────┘
         ▲
         │ HTTP / WebSocket
┌─────────────────────────────────────────────────────┐
│               Frontend  (Next.js 14 / TypeScript)   │
│                                                     │
│  ┌─────────────────┐   ┌──────────────────────────┐ │
│  │  אירועים חיים  │   │  צלילה עמוקה לאירוע      │ │
│  │  /live          │   │  /incidents/[id]         │ │
│  └─────────────────┘   └──────────────────────────┘ │
│  ┌─────────────────┐   ┌──────────────────────────┐ │
│  │  בסיס ידע      │   │  לוח אוטונומיה           │ │
│  │  /knowledge     │   │  /autonomy               │ │
│  └─────────────────┘   └──────────────────────────┘ │
│  ┌─────────────────┐                                │
│  │  ביצועים       │   Zustand + React Query        │
│  │  /performance   │   Radix UI + Tailwind          │
│  └─────────────────┘                                │
└─────────────────────────────────────────────────────┘
```

---

## זרימת נתונים — מהתראה לפתרון

```
1. Grafana שולחת webhook  ──▶  POST /api/v1/webhooks
                                      │
2. צינור Triage                       ▼
   ├── טביעת אצבע (hash של labels)
   ├── כפילויות (Redis TTL)
   ├── קורלציה (קיבוץ התראות קשורות → אירוע)
   └── סיווג (physical / data_integrity / coupling)
                                      │
3. העשרת הקשר                        ▼
   ├── חיפוש דמיון ב-IKB (pgvector)
   ├── בסיסי ייחוס לשרת
   └── דפוסים היסטוריים
                                      │
4. סוכן חקירה                         ▼
   ├── לולאת שימוש בכלים (Anthropic claude-sonnet)
   ├── הרצת כלים מהרישום (Grafana, SSH, ועוד)
   └── מייצר ראיות מובנות + פעולה מומלצת
                                      │
5. כרטיס Jira                         ▼
   └── נוצר עם ראיות מלאות, חומרה, רמת פעולה
                                      │
6. עדכון UI בזמן אמת                  ▼
   └── שידור WebSocket ← דף אירועים חיים
                                      │
7. משוב על פתרון                      ▼
   ├── מפעיל פותר + שולח משוב
   ├── IKB מתעדכן עם דפוס פתרון חדש
   ├── מדדים מתעדכנים
   └── רמת אוטונומיה עשויה לעלות
```

---

## מבנה Backend

```
backend/
├── app/
│   ├── main.py                  # אפליקציית FastAPI, middleware, נתיבים
│   ├── config.py                # הגדרות Pydantic (משתני סביבה)
│   ├── database.py              # מנוע SQLAlchemy אסינכרוני + session factory
│   ├── api/v1/                  # מטפלי נתיבים
│   │   ├── webhooks.py
│   │   ├── incidents.py
│   │   ├── feedback.py
│   │   ├── websocket.py
│   │   ├── metrics.py
│   │   ├── knowledge.py
│   │   └── autonomy.py
│   ├── models/                  # מודלי ORM של SQLAlchemy
│   ├── schemas/                 # סכמות Pydantic לבקשות/תגובות
│   ├── services/
│   │   ├── triage/              # טביעת אצבע, כפילויות, קורלציה, מסווג
│   │   ├── ikb/                 # בסיס ידע אירועים + embeddings
│   │   ├── agent/               # חוקר, מבצע, פרומפטים, מנתח
│   │   ├── autonomy/            # מנהל רמות, מצב צל, מפסק זרם
│   │   ├── jira/                # לקוח, יצירת כרטיסים, סנכרון, תבניות
│   │   └── feedback/            # תזמור, זיהוי דפוסים, מדדים
│   └── tools/
│       ├── base.py              # מחלקת Tool בסיסית (abstract)
│       ├── registry.py          # רישום כלים מרכזי
│       ├── executor.py          # הרצת כלים עם timeout וטיפול בשגיאות
│       └── examples/            # כלים לדוגמה: Grafana, SSH, רעננות נתונים
├── alembic/                     # מיגרציות DB (5 מיגרציות)
├── config/
│   ├── classification_rules.yaml
│   └── actions.yaml             # 11 רמות פעולה
├── tests/
├── docker-compose.yml           # PostgreSQL 15 (pgvector) + Redis 7
├── pyproject.toml
└── .env.example
```

---

## מבנה Frontend

```
frontend/
├── app/
│   ├── layout.tsx               # פריסת שורש: QueryProvider + WebSocketProvider + ThemeProvider
│   └── (dashboard)/
│       ├── live/                # אירועים חיים (WebSocket בזמן אמת)
│       ├── incidents/[id]/      # צלילה עמוקה לאירוע
│       ├── knowledge/           # חיפוש IKB + סינונים
│       ├── performance/         # מדדי איכות ותפעול
│       └── autonomy/            # ניהול רמות + מתג כיבוי
├── components/
│   ├── incidents/               # IncidentRow, Header, StatsBar, FilterBar, ActionBar
│   ├── analysis/                # AgentReasoning, AnalysisPanel, IKBContextPanel
│   └── common/                  # SeverityBadge, CategoryBadge, ConfidenceBar, RelativeTime
├── lib/
│   ├── api.ts                   # לקוח fetch מרכזי → /api/v1
│   ├── store.ts                 # מאגרי מצב Zustand
│   └── websocket.ts             # לקוח WebSocket + provider
├── next.config.js               # rewrites: /api/v1 → localhost:8000
├── tailwind.config.ts
└── package.json
```

---

## עקרונות עיצוב מרכזיים

| עיקרון | מימוש |
|---|---|
| דטרמיניסטי קודם, AI אחר כך | ה-triage המרכזי מבוסס חוקים; AI מוסיף פרשנות מעל |
| אסינכרוני לחלוטין | כל קוד Python משתמש ב-`async/await`, asyncpg, SQLAlchemy async |
| לוגינג מובנה | structlog + X-Request-ID לאורך כל השכבות |
| צל לפני אוטונומיה | פעולות רצות במצב צל, מאומתות לפני הרצה אמיתית |
| לולאת משוב | נתוני פתרון מעדכנים IKB + מדדים + רמת אוטונומיה |
| דפוס רישום כלים | כלים נרשמים עם decorator, סכמת Anthropic מיוצרת אוטומטית |

---

## סיווג התראות

מוגדר ב-`config/classification_rules.yaml`:

| קטגוריה | אותות |
|---|---|
| `physical` | CPU, זיכרון, דיסק, I/O, עומס, טמפרטורה, חומרה |
| `data_integrity` | רעננות, פערים, pipeline, עיכוב ETL, סחיפת סכמה |
| `coupling` | BGP, peers, קישורים, sessions, זמן תגובה, tunnels, OSPF, ISIS |

---

## רמות אוטונומיה

מוגדר ב-`config/actions.yaml` — 11 רמות מהפחות להכי משמעותית:

| # | שם | תיאור |
|---|---|---|
| 1 | `NOTE_IN_TICKET` | הוספת הערת ניתוח לכרטיס Jira |
| 2 | `ALERT_OWNER` | פינג לבעל ההתראה בכרטיס |
| 3 | `CREATE_INCIDENT_CHANNEL` | יצירת ערוץ תקשורת |
| 4 | `SILENCE_ALERT` | השתקת התראה ב-Grafana |
| 5 | `SCALE_OUT_REPLICAS` | הוספת replicas |
| 6 | `BOUNCE_SERVICE` | הפעלה מחדש של שירות |
| 7 | `ROLLBACK_DEPLOYMENT` | ביטול deployment אחרון |
| 8 | `FLUSH_CACHE` | ניקוי caches |
| 9 | `FAILOVER_TRAFFIC` | ניתוב מחדש של תעבורה |
| 10 | `QUARANTINE_HOST` | בידוד שרת |
| 11 | `REBOOT_HOST` | הפעלה מחדש מלאה של שרת |

---

## משתני סביבה

צור `backend/.env` על בסיס `backend/.env.example`:

```dotenv
# מסד נתונים
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/promt_agent
DATABASE_POOL_SIZE=10
DATABASE_MAX_OVERFLOW=20

# Redis
REDIS_URL=redis://localhost:6379

# CORS
CORS_ORIGINS=["http://localhost:3000"]

# מודל שפה
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

## הרצה מקומית — Quick Start

### דרישות מוקדמות

- Python 3.11+
- Node.js 18+
- Docker + Docker Compose

### שלב 1 — תשתית (PostgreSQL + Redis)

```bash
cd backend
docker-compose up -d
```

מפעיל:
- PostgreSQL 15 עם pgvector על פורט `5432`
- Redis 7 על פורט `6379`

### שלב 2 — Backend

```bash
cd backend

# העתק והשלם משתני סביבה
cp .env.example .env
# ערוך .env עם ANTHROPIC_API_KEY, פרטי Jira, וכו׳

# התקנת תלויות
pip install -e ".[dev]"

# הרצת מיגרציות מסד נתונים
python -m alembic upgrade head

# הפעלת השרת
uvicorn app.main:app --reload --port 8000
```

Backend רץ על: `http://localhost:8000`  
תיעוד API (Swagger): `http://localhost:8000/docs`  
בדיקת זמינות: `http://localhost:8000/health`

### שלב 3 — Frontend

```bash
cd frontend

npm install
npm run dev
```

Frontend רץ על: `http://localhost:3000`

---

## פריסה לפרודקשן

### Docker Compose (מומלץ לשרת יחיד)

צור `docker-compose.prod.yml`:

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

הרצה:
```bash
docker-compose -f docker-compose.prod.yml up -d
```

### Dockerfile ל-Backend (הוסף ל-`backend/Dockerfile`)

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY pyproject.toml .
RUN pip install -e ".[prod]"
COPY . .
RUN alembic upgrade head
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

### Dockerfile ל-Frontend (הוסף ל-`frontend/Dockerfile`)

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

## מפת תקשורת בין שירותים

```
Frontend (3000)
    │
    ├── HTTP REST ──▶ Backend API (8000)   [דרך rewrites של Next.js]
    └── WebSocket ──▶ /api/v1/ws (8000)

Backend (8000)
    ├── PostgreSQL (5432)                  [SQLAlchemy async]
    ├── Redis (6379)                       [aioredis — cache + pub/sub]
    ├── Anthropic API (HTTPS חיצוני)       [anthropic SDK]
    ├── Jira API (HTTPS חיצוני)            [httpx async client]
    └── Grafana API (HTTPS חיצוני)         [קריאות כלים]
```

---

## ניטור ותצפיתיות

| Endpoint | מטרה |
|---|---|
| `GET /health` | בדיקת זמינות — מחזיר `{"status": "ok"}` |
| `GET /api/v1/metrics` | מדדים תפעוליים (triaged, resolved, MTTR, דיוק) |
| `GET /api/v1/metrics/quality` | ניקוד איכות הסוכן לפי קטגוריה |

לוגים הם JSON מובנה דרך `structlog` עם `request_id` לקורלציה בכל שורה.

---

## הערות אבטחה

- נקודת הקצה של Grafana מאמתת את `GRAFANA_WEBHOOK_SECRET` דרך HMAC
- טוקן Jira מאוחסן רק במשתני סביבה, אף פעם לא ב-DB
- CORS מוגבל ל-`CORS_ORIGINS` המוגדרים
- כל שאילתות DB משתמשות בפרמטרים מוגנים דרך SQLAlchemy ORM (ללא סיכון SQL injection)
- פעולות אוטונומיות מעל רמה 5 דורשות קידום מפורש דרך אימות במצב צל
