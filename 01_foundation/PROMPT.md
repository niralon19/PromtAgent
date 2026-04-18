# Stage 01 - Foundation (Backend Scaffolding)

## מטרת השלב

לבנות את השלד של ה-backend: FastAPI app, DB schema, Pydantic models, webhook endpoint בסיסי,
והגדרות של logging, config, ו-testing. בסוף השלב - webhook מקבל Grafana alert, שומר ב-DB,
ומחזיר 200. זה הבסיס שכל יתר השלבים נבנים מעליו.

## הקשר מוקדם

ראה `CLAUDE.md` בשורש הפרויקט לקונטקסט המלא.
המערכת כבר קיימת כ-PoC אצל המשתמש - **אל תמציא מבנה חדש בסתירה לקיים**. 
שאל לראות קוד קיים אם רלוונטי.

---

## PROMPT (להעברה ל-Claude)

```
אני מתחיל את שלב הבסיס של פרויקט ה-NOC Agent שמתואר ב-CLAUDE.md.

המטרה של הסשן הזה: לבנות את השלד של ה-backend עם:

1. מבנה תיקיות מלא לפי CLAUDE.md
2. pyproject.toml עם כל התלויות (FastAPI, Pydantic v2, SQLAlchemy 2.0 async, 
   asyncpg, Alembic, structlog, httpx, pytest, pytest-asyncio, testcontainers, 
   anthropic, redis.asyncio)
3. docker-compose.yml לפיתוח מקומי (PostgreSQL 15 עם pgvector, Redis)
4. app/core/config.py - Settings class עם pydantic-settings, קורא מ-env
5. app/core/logging.py - הגדרת structlog עם JSON output בפרוד וקריא בפיתוח
6. app/db/base.py - DeclarativeBase עם async session setup
7. app/db/session.py - async session factory + dependency
8. app/db/models.py - SQLAlchemy models ראשוניים: Alert, Incident
9. app/schemas/alert.py - Pydantic models ל-GrafanaAlert (לפי פורמט webhook סטנדרטי)
10. app/schemas/incident.py - Pydantic models ל-Incident (כולל כל השדות מ-CLAUDE.md)
11. app/api/webhooks.py - POST /webhooks/grafana endpoint:
    - ולידציה של payload
    - שמירת raw alert ב-DB
    - יצירת Incident בסטטוס "triaging"
    - החזרת 202 Accepted עם incident_id
12. app/main.py - FastAPI app עם:
    - lifespan context (init DB pool, init redis, cleanup)
    - middleware ל-request ID + structured logging
    - error handlers
    - CORS אם נדרש
    - הרישום של כל ה-routers
13. alembic/ - init + first migration שיוצרת את הטבלאות
14. tests/ - conftest.py עם fixtures ל-async client ו-DB, בדיקה אחת end-to-end 
    של webhook (שולח payload, מוודא 202, מוודא שהרשומות נשמרו)

דרישות איכות:
- Type hints מלאים כולל return types
- `from __future__ import annotations` בכל קובץ
- async/await לכל I/O
- structlog עם context binding (alert_id, incident_id) בכל log
- explicit exception types
- dependency injection דרך FastAPI Depends
- בלי global state

מגבלות חשובות:
- **אל תממש לוגיקת triage עדיין** - זה שלב הבא. כרגע רק מקבלים ושומרים.
- אל תתחיל לעבוד על IKB/embeddings/agent - זה שלבים מאוחרים יותר.
- אם משהו לא ברור - שאל לפני שאתה מנחש.

התחל בהצגת עץ תיקיות מלא, ואז תן את הקבצים בזה אחר זה. אחרי כל קובץ ארוך, 
תן לי להגיד "continue" לפני הבא (שלא נגיע ל-context limit).
```

---

## CHECKLIST - מה צריך להיות מוכן בסוף

- [ ] docker-compose.yml עולה (postgres + redis) בהצלחה
- [ ] `alembic upgrade head` רץ ויוצר טבלאות
- [ ] `uvicorn app.main:app --reload` עולה בלי שגיאות
- [ ] POST לwebhook מחזיר 202 ושומר ב-DB
- [ ] `pytest` עובר
- [ ] לוגים מודפסים ב-structured format
- [ ] GET /health מחזיר 200 עם סטטוס DB ו-Redis

## שאלות להבהיר לפני/בזמן הסשן

1. האם יש PostgreSQL/Redis כבר ב-cluster שלך או שצריך להרים?
2. איזה format של Grafana webhook אתה מקבל? (יש שני פורמטים - old-style וNew unified alerting)
3. האם יש דרישות ספציפיות לauth (OAuth, mTLS) כבר בשלב הזה?
4. האם אתה עובד עם monorepo (backend+frontend) או רפוזיטורים נפרדים?

## פלט צפוי

אחרי הסשן הזה, יש לך **backend scaffolding עובד** שעליו נבנה ה-triage, ה-enrichment, וכל השאר.
הקוד שלך הקיים (webhook receiver, router) - נעטוף אותו בשלב הבא לתוך המבנה החדש,
או נשמר אותו כ-reference ונבנה מחדש לפי הסטנדרטים - בהתאם לאיכות הקיים.
