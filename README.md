# NOC Intelligent Alert Management System - Prompt Package

מערכת פרומטים מובנית לבנייה הדרגתית של מערכת NOC חכמה לניהול התראות.
המערכת מקבלת התראות מ-Grafana, מנתבת לפי קטגוריה, חוקרת אוטונומית
באמצעות סוכני AI, ופותחת טיקטים מובנים ב-Jira עם המלצות לפעולה.

## מבנה החבילה

```
PromtAgent/
├── 00_master/                 # CLAUDE.md הראשי - פרומט מנחה לכל הפרויקט
├── 01_foundation/             # תשתית: FastAPI, DB, schemas
├── 02_tool_registry/          # Tool Registry - שילוב קוד קיים
├── 03_triage/                 # ניתוב, fingerprinting, dedup
├── 04_ikb/                    # Incident Knowledge Base + pgvector
├── 05_investigator_agent/     # Agent עם Anthropic SDK tool use
├── 06_jira_integration/       # Jira API + structured tickets
├── 07_feedback_loop/          # למידה מ-resolution
├── 08_ui_scaffolding/         # Next.js setup
├── 09_live_operations/        # מסך Live Operations
├── 10_incident_deep_dive/     # מסך Incident Deep Dive
├── 11_performance_dashboard/  # מסך מטריקות איכות
├── 12_knowledge_explorer/     # מסך חיפוש ב-IKB
├── 13_autonomy/               # מדרג פעולות אוטונומיות
└── 99_references/             # schemas, הנחיות ודוגמאות
```

## איך להשתמש

### שלב 0 - הגדרה ראשונית

1. **העתק את** `00_master/CLAUDE.md` **לשורש הפרויקט שלך** (הריפו שבו המערכת נבנית, לא הריפו הזה).
2. זה יהיה המסמך המנחה לכל סשן עבודה עם Claude Code / Claude.ai.

### שלב 1 - עבודה לפי סדר

כל תיקייה מכילה:
- `PROMPT.md` - הפרומט לסשן בסשן ייעודי
- `CHECKLIST.md` - מה צריך להיות מוכן בסוף השלב
- לפעמים גם קבצי עזר (schemas, דוגמאות)

**סדר מומלץ:**

1. 01_foundation - השלד הבסיסי (חובה ראשון)
2. 02_tool_registry - שילוב הקוד הקיים שלך
3. 03_triage - מניעת רעש מההתחלה
4. 06_jira_integration - tickets איכותיים מההתחלה (חשוב ל-feedback)
5. 04_ikb - זיכרון (לפני Agent, כך Agent נהנה ממנו)
6. 05_investigator_agent - המוח
7. 07_feedback_loop - סגירת המעגל ללמידה
8. 08-12 - UI בהדרגה
9. 13_autonomy - רק אחרי 2-3 חודשי ריצה

### שלב 2 - איך להשתמש בפרומט ספציפי

בסשן חדש:

```
"אני עובד על פרויקט NOC Agent. הסביבה מתוארת ב-CLAUDE.md בשורש הפרויקט.
היום אני עובד על שלב 03_triage. הנה הפרומט:

[הדבק תוכן PROMPT.md של השלב]

הקוד הקיים שלי שרלוונטי:
[הדבק קטעי קוד קיימים או ציין paths]"
```

## עקרונות מנחים

1. **Deterministic workflow בבסיס, AI מעליו** - לא להחליף, להוסיף
2. **Feedback loop הוא ה-DNA** - בלי resolution data נאסף, שום למידה לא תקרה
3. **Shadow mode לפני כל autonomous action** - ללא יוצא מן הכלל
4. **Observability מהיום הראשון** - traces, metrics, structured logs
5. **מטריקות קובעות קצב, לא לוח זמנים** - מעבר ל-autonomy לפי איכות

## הערות

- הפרומטים תוכננו לעבודה עם Claude Sonnet 4.5+ או Claude Opus 4+
- סגנון קוד: Python עם type hints מלאים, Pydantic v2, async/await, structlog
- Frontend: Next.js 14 App Router, TypeScript strict, Tailwind + shadcn/ui

---

בהצלחה בבניה 🚀
