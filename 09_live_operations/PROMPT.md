# Stage 09 - Live Operations Dashboard

## מטרת השלב

המסך הראשון שה-NOC engineer רואה. רשימה live של incidents פעילים, ממוינת לפי 
severity + confidence, עם actions מהירות ו-real-time updates.

## הקשר מוקדם

ראה `CLAUDE.md`. UI scaffolding (08) הושלם.

---

## PROMPT (להעברה ל-Claude)

```
אני עובד על פרויקט NOC Agent שמתואר ב-CLAUDE.md. UI scaffolding (שלב 08) 
הושלם.

בסשן הזה אני בונה את המסך הראשון: Live Operations Dashboard.

דרישות פונקציונליות:
- רשימת incidents פעילים (status != resolved, false_positive)
- ממוין לפי severity (critical > warning > info) ואז לפי age
- Live update דרך WebSocket (incident חדש מופיע למעלה, סטטוסים מתחלפים)
- Filter bar: category, severity, datacenter, status
- כל שורה: severity icon | host | category badge | alert name | age | 
  status | confidence bar | actions (3 dots menu)
- קליק על שורה → ניווט ל-/incidents/[id]
- Actions מהשורה: Acknowledge, Mark False Positive, Escalate
- Empty state יפה כשאין incidents פעילים ("All systems nominal ✓")
- Loading state עם skeleton
- Error boundary

דרישות טכניות:

1. app/(dashboard)/live/page.tsx:
   - Server component שטוען initial data
   - מעביר ל-client component עם live updates

2. app/(dashboard)/live/LiveIncidentsList.tsx ('use client'):
   - useIncidents hook עם filters
   - useWebSocket subscription ל-"incidents.*" topic
   - merge של initial data + live updates (TanStack Query cache mutation)
   - virtual scrolling אם >100 items (react-virtuoso או tanstack-virtual)

3. components/incident/IncidentRow.tsx:
   - דחוס, קריא, clickable
   - Severity: icon + color (critical=red, warning=amber, investigating=blue, 
     resolved=emerald)
   - Host: monospace, truncate עם tooltip לfull
   - Category: badge עם צבע יציב לכל קטגוריה
   - Age: relative time (auto-refresh)
   - Status: text + spinner אם investigating
   - Confidence: bar 0-100 עם צבע שמתאים (אדום אם <50, צהוב 50-75, ירוק >75)
   - Actions: DropdownMenu עם Acknowledge / False Positive / Escalate / 
     View Details

4. components/incident/FilterBar.tsx:
   - Multi-select לקטגוריות
   - Severity buttons (toggleable)
   - Datacenter dropdown (מוזן מ-API)
   - Status dropdown
   - Clear filters button
   - Active filters מוצגים כ-chips ניתנים להסרה

5. components/incident/EmptyState.tsx:
   - כאשר אין incidents: illustration פשוטה + "All systems nominal"
   - כאשר יש filters active בלי תוצאות: "No incidents match filters"

6. components/incident/StatsBar.tsx (בסיד):
   - Total active | Critical | Today's count | Resolved today
   - Link ל-Performance page

7. WebSocket events שצריך לטפל בהם:
   - incident.created - insert בראש
   - incident.updated - update in place
   - incident.investigation_started - status change
   - incident.investigation_completed - confidence + hypothesis updated
   - incident.resolved - remove (or grey out with fade)

8. Actions logic:
   - Acknowledge: POST /incidents/{id}/acknowledge (optimistic update)
   - False Positive: confirm dialog (irreversible), POST /incidents/{id}/false-positive
   - Escalate: dialog to choose tier/team, POST /incidents/{id}/escalate

9. Accessibility:
   - Rows navigable by keyboard (arrow keys or Tab)
   - Enter על row → ניווט
   - Actions dropdown accessible
   - ARIA labels נכונים

10. Tests (Playwright):
    - Initial load מציג incidents
    - Filter עובד
    - Click על row מנווט
    - Actions מטריגרים POST נכון
    - WebSocket update מוסיף incident חדש

דגשים:
- Performance: 500+ incidents active (אם נפל אירוע רחב) - חייב לעבוד חלק
- Density: על מסך 1080p צריך לראות 20-30 שורות בלי scrolling
- Live updates: flash/pulse קצר כשrow מתעדכן (Framer Motion)
- אל תוסיף אנימציות מיותרות - זה NOC, לא landing page

שאלות להבהיר:
- האם יש role-based access (NOC viewer vs admin)? אם כן, מי יכול לעשות 
  False Positive?
- מה ההעדפה לsorting: שנייה ראשית הוא severity (recommended) או age?

התחל במבנה, אחר כך components מבוטחים, אחר כך integration.
```

---

## CHECKLIST

- [ ] רשימה נטענת ומציגה incidents אמיתיים
- [ ] Filters עובדים ומשתמרים ב-URL (shareable link)
- [ ] WebSocket updates מופיעים live
- [ ] Actions עובדים ומעדכנים state
- [ ] Empty/Loading/Error states נראים טוב
- [ ] Dark mode עקבי
- [ ] Keyboard navigation
- [ ] תגובה מהירה גם ב-500+ items

## פלט צפוי

NOC engineer נכנס למערכת ורואה בשנייה את כל התמונה. יודע במה לטפל, באיזה סדר, 
ויכול לעשות triage ראשוני בלי להיכנס לעומק.
