# Stage 12 - Knowledge Base Explorer

## מטרת השלב

מסך שמאפשר ל-engineer לגלוש ב-IKB: לחפש סמנטית, לראות patterns, ללמוד 
מ-incidents היסטוריים. הופך את ה-knowledge base לכלי ארגוני ולא רק ל-backend.

## הקשר מוקדם

ראה `CLAUDE.md`. IKB (שלב 04) ו-Feedback Loop (שלב 07) מזינים דאטה עשיר.

---

## PROMPT (להעברה ל-Claude)

```
אני עובד על פרויקט NOC Agent שמתואר ב-CLAUDE.md. שלבים 04 (IKB) ו-07 (feedback 
loop) צוברים היסטוריה עשירה של incidents עם resolutions ו-embeddings.

בסשן הזה אני בונה את Knowledge Explorer - הממשק שהופך את הידע ל-browsable.

דרישות פונקציונליות:

1. Search Bar (top):
   - חיפוש חופשי (semantic + keyword מעורב)
   - דוגמה: "BGP flap after maintenance" ימצא incidents דומים גם אם המילים 
     המדויקות לא מופיעות
   - Autocomplete עם hosts, alertnames נפוצים
   - Keyboard shortcut: Cmd/Ctrl+K

2. Filters (sidebar):
   - Category
   - Date range
   - Hostname (multi-select)
   - Resolution category (multi-select)
   - Was hypothesis correct (yes/partial/no)
   - Has ticket in Jira (bool)
   - Recurrence count (slider)

3. Results view:
   - Cards list, כל card:
     * Title: hostname + alertname
     * Date + resolution time
     * Category badge
     * Short hypothesis
     * Resolution category badge
     * Was correct indicator
     * Similarity score (אם search נעשה)
   - Infinite scroll / pagination
   - Sort: relevance (default) | newest | oldest | recurrence

4. Incident page (detailed):
   - link ל-/knowledge/[id] (read-only view)
   - כל המידע על ה-incident ההיסטורי:
     * Full alert context
     * Tools שרצו ותוצאותיהם
     * Agent reasoning (מ-agent_run_steps)
     * Final hypothesis + confidence
     * Actual resolution
     * What worked? (מ-feedback)
   - "Similar incidents" פנל בצד
   - Comments / annotations section (Teach Mode - ראה למטה)

5. Teach Mode:
   - engineer יכול להוסיף annotations ל-incidents היסטוריים:
     * "The real root cause was X, the agent's hypothesis was wrong because Y"
     * "This resolution works only if Z condition is met"
     * "Related to maintenance window on DATE"
   - annotations נשמרים ומשפיעים על future retrievals (via embedding)
   - רק trusted users (NOC seniors) יכולים להוסיף

6. Patterns View:
   - Tab משני: /knowledge/patterns
   - מציג את ה-patterns שזוהו ב-feedback loop:
     * Common resolutions per category
     * Hosts with recurring issues
     * Time-based patterns (שעות מסוימות, ימים בשבוע)
     * Resolution time trends

7. Insights View:
   - "Top 10 most common issues this quarter"
   - "Fastest-resolved vs slowest-resolved categories"
   - "Issues where hypothesis was consistently wrong" - לחקור מה חסר ל-agent
   - Data-driven suggestions: "Consider adding a tool for X based on manual 
     investigations showing Y"

דרישות טכניות:

1. app/(dashboard)/knowledge/page.tsx - main explorer
   app/(dashboard)/knowledge/[id]/page.tsx - detailed incident
   app/(dashboard)/knowledge/patterns/page.tsx - patterns view
   app/(dashboard)/knowledge/insights/page.tsx - insights view

2. Backend endpoints:
   - GET /knowledge/search?q=...&filters=... - semantic + keyword search
   - GET /knowledge/incidents/{id} - full historical view
   - POST /knowledge/incidents/{id}/annotations - add annotation (auth)
   - GET /knowledge/patterns
   - GET /knowledge/insights

3. Search implementation:
   - backend: combine pgvector similarity + full-text search (ts_vector על 
     hypothesis + resolution)
   - hybrid ranking: 0.7 * similarity + 0.3 * keyword_score
   - filters מתווספים לquery

4. Components:
   - components/knowledge/SearchBar.tsx עם keyboard shortcut
   - components/knowledge/FilterSidebar.tsx
   - components/knowledge/IncidentCard.tsx (קצר)
   - components/knowledge/IncidentDetail.tsx (ארוך)
   - components/knowledge/AnnotationEditor.tsx
   - components/knowledge/PatternCard.tsx

5. Performance:
   - search results cached (TanStack Query)
   - Infinite scroll עם batch של 20
   - debounce על search input (300ms)
   - prefetching של incident details on hover

6. Export:
   - "Download as Markdown" - לשיתוף ב-runbooks
   - "Copy link" - לשיתוף פנימי

7. Sharing:
   - URL includes search + filters - shareable
   - Breadcrumbs ל-navigation חוזר

דגשים:
- זה לא חיפוש Google. זה כלי מקצועי לאנג'ינרים. UX דחוס, כולל hot keys.
- Teach Mode הוא הזהב - אם engineer seniors משקיעים 15 דקות בשבוע להוסיף 
  annotations, המערכת משתפרת דרמטית.
- הצג את ה-agent's reasoning (גם כשהוא טעה!) - זה חינוכי ובונה אמון.
- Annotations מחייבים re-embedding של ה-incident (רקע job).

שאלות להבהיר:
- האם אתה רוצה public sharing של incidents (URL-based without auth) או רק 
  internal?
- מי יכול להוסיף annotations? (kol team members vs seniors)
- Retention: כמה זמן להחזיק incidents ב-IKB? (חצי שנה? שנה? לנצח?)

התחל ב-search + results, אחר כך incident detail, אחר כך patterns & teach mode.
```

---

## CHECKLIST

- [ ] Semantic search עובד ומחזיר תוצאות רלוונטיות
- [ ] Filters משולבים בתוצאות חיפוש
- [ ] Incident detail view מלא
- [ ] Teach Mode עובד (annotations נשמרות ומשפיעות)
- [ ] Patterns view מציג דפוסים
- [ ] Shareable URLs (search + filter state)
- [ ] Export (markdown) עובד

## פלט צפוי

ה-IKB הופך לכלי שצוותים משתמשים בו יומיומית - לא רק ל-enrich agent, אלא 
כ-reference ללימוד עצמי ו-onboarding.
