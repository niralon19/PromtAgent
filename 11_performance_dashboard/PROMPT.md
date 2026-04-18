# Stage 11 - Agent Performance Dashboard

## מטרת השלב

Dashboard שמאפשר לך (tech lead) ול-management לראות את איכות המערכת לאורך זמן, 
ולקבל החלטות מבוססות-דאטה על מעבר ל-autonomous remediation.

## הקשר מוקדם

ראה `CLAUDE.md`. שלב 07 (feedback loop) כבר צובר את הדאטה. שלבים 08-10 של UI 
הושלמו.

---

## PROMPT (להעברה ל-Claude)

```
אני עובד על פרויקט NOC Agent שמתואר ב-CLAUDE.md. ה-backend צובר action_metrics, 
host_statistics, ו-patterns; ה-UI scaffold + Live Ops + Deep Dive מוכנים.

בסשן הזה אני בונה את Performance Dashboard - כלי הניהול של המערכת.

Sections:

1. Quality Metrics (top):
   - Hypothesis accuracy over time (line chart, per category):
     * X: זמן (7d/30d/90d toggles)
     * Y: accuracy %
     * 3 lines: physical, data_integrity, coupling
   - Overall accuracy KPI card (גדול)
   - False positive rate card
   - Avg confidence calibration card (האם confidence 80% = 80% success?)

2. Operational Metrics:
   - Incidents per day (bar chart) עם breakdown לper category
   - MTTR breakdown (stacked bar):
     * Time to triage | Time to investigate | Time to resolve
     * per category
   - Dedup rate over time
   - Cost per investigation (histogram)
   - Top expensive investigations (table - לבדיקה של outliers)

3. Progression to Autonomy (THE MONEY SECTION):
   - Table of action types:
     * Action name
     * Total samples
     * Precision % (עם progress bar)
     * Current tier
     * Streak days without error
     * Readiness indicator:
       - 🔴 Not ready (<50 samples or <80% precision)
       - 🟡 Approaching (80-89% precision, <200 samples)
       - 🟢 Ready for tier promotion
     * Action button: "Promote to tier X" (admin only)
   - סדר הטבלה: ready first, then approaching, then not-ready
   - Historical view: graph של precision per action לאורך זמן

4. Patterns & Anomalies:
   - Recurring hosts (table):
     * hostname, incidents count (30d), common resolution, recommended action
   - Emerging alert types:
     * alertname, first seen, count, category assigned
   - Resolution patterns (insights):
     * "87% of data_integrity incidents this week resolved via 
       ETL_RESTART - consider investigating root cause"

5. System Health:
   - Backend components status (webhook, triage, agent, jira sync)
   - Queue depths (triage queue, agent queue)
   - LLM provider status + rate limit remaining
   - Database connection pool usage

דרישות טכניות:

1. app/(dashboard)/performance/page.tsx:
   - Dashboard layout עם sections
   - Date range selector (7d/30d/90d/custom)

2. Charts:
   - Tremor כדאי כאן: Cards + Charts + NumberMetrics באותה ספריה
   - Alternative: Recharts אם Tremor לא מתאים
   - כל chart: dark theme matching

3. Components:
   - components/performance/QualityMetricsSection.tsx
   - components/performance/OperationalMetricsSection.tsx
   - components/performance/AutonomyTable.tsx (הכי חשוב!)
   - components/performance/PatternsSection.tsx
   - components/performance/SystemHealthSection.tsx

4. Hooks:
   - useQualityMetrics(dateRange)
   - useOperationalMetrics(dateRange)
   - useActionProgression()
   - usePatterns(dateRange)
   - useSystemHealth() - עם polling כל 30 שניות

5. Backend endpoints (אם חסרים):
   - GET /metrics/quality?range=30d
   - GET /metrics/operational?range=30d
   - GET /metrics/autonomy-candidates
   - GET /patterns?range=30d
   - GET /system/health
   - POST /actions/{action_key}/promote (admin)

6. Export capabilities:
   - כל section: button "Export CSV" לדאטה גולמית
   - "Generate Report" (PDF עם כל המדדים לרבעון)

7. Role-based:
   - View: כל NOC user
   - Promote action to higher tier: admin only

8. Alerts בתוך הdashboard:
   - אם accuracy יורד מ-X% - banner אזהרה
   - אם cost per investigation > Y - banner
   - אם queue depth > Z - banner

דגשים:
- **זה dashboard של management decisions**. צריך להיות ברור בבת אחת מה מצב 
  המערכת.
- Autonomy table הוא הסיבה הכי חשובה שהמסך קיים - לתת לה מקום מרכזי.
- Empty states: בתחילת ריצה לא יהיה מספיק דאטה. אל תציג charts ריקים - הצג 
  "Insufficient data - X samples needed".
- Thresholds (80% precision, 200 samples) צריכים להיות ב-config ולא hardcoded.

שאלות להבהיר:
- איזה thresholds אתה רוצה לresponse to autonomy readiness?
- מי יקבל notification כשaction מוכן ל-promotion?
- האם יש SLA מוגדר לMTTR שצריך להציג כקו אופק בgraph?

התחל ב-Autonomy Table (הכי חשוב), אחר כך quality metrics, אחר כך השאר.
```

---

## CHECKLIST

- [ ] Quality metrics מוצגים עם ranges שונים
- [ ] Autonomy table עם readiness indicators עובדת
- [ ] Patterns & anomalies מופיעים בזמן אמת
- [ ] System health מתעדכן
- [ ] Export CSV עובד לכל section
- [ ] Empty states לדאטה ראשוני
- [ ] Admin-only actions מוגנים

## פלט צפוי

**המסך שמאפשר לך להחליט מתי לעבור ל-autonomous.** בלי זה, אתה מנחש. עם זה, 
יש לך raw material לקבלת החלטות, ולשיחות עם management על הערך של המערכת.
