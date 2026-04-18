# Stage 08 - UI Scaffolding (Next.js + Tailwind + shadcn/ui)

## מטרת השלב

להקים את תשתית ה-frontend: Next.js 14 App Router, TypeScript strict, Tailwind, 
shadcn/ui, WebSocket provider, API client, layout ראשי, ו-dark mode. בסוף השלב: 
יש מסגרת שכל המסכים הבאים נבנים בתוכה.

## הקשר מוקדם

ראה `CLAUDE.md`. Backend שלבים 01-07 הושלמו; יש API עובד ו-WebSocket endpoint 
ב-backend.

---

## PROMPT (להעברה ל-Claude)

```
אני עובד על פרויקט NOC Agent שמתואר ב-CLAUDE.md. Backend מלא (שלבים 01-07).

בסשן הזה אני מקים את ה-frontend. Next.js 14 App Router, TypeScript strict, 
Tailwind + shadcn/ui, dark-first, עם חיבור ל-backend.

דרישות:

1. Project setup:
   - Next.js 14 (App Router) + TypeScript strict
   - Tailwind CSS + shadcn/ui (init + רכיבים בסיסיים: button, card, input, 
     badge, table, dialog, dropdown-menu, tabs, separator, scroll-area, toast)
   - Tremor ל-charts (alternative: Recharts)
   - TanStack Query + Zustand
   - package.json עם scripts: dev, build, lint, typecheck

2. Directory structure (ראה CLAUDE.md frontend section)

3. app/layout.tsx:
   - RootLayout עם:
     * ThemeProvider (next-themes) - dark כ-default
     * QueryClientProvider
     * WebSocketProvider
     * Toaster
   - Font: Inter (variable) + JetBrains Mono ל-technical text
   - Global styles: CSS variables לצבעים, מפה ל-Tailwind tokens

4. app/(dashboard)/layout.tsx:
   - Sidebar navigation עם links ל-4 המסכים:
     * Live Operations (/live)
     * Incidents (/incidents) - או ישיר ל-/incidents/[id]
     * Performance (/performance)
     * Knowledge (/knowledge)
   - Top bar: search (גלובלי על incidents), theme toggle, user menu, 
     connection status indicator
   - ScrollArea עבור main content

5. components/providers/WebSocketProvider.tsx:
   - Single connection, reconnect logic עם exponential backoff
   - Context API שמפיץ events לconsumers
   - useWebSocket hook שמאפשר subscribe לtopic מסוים
   - Connection status indicator (exposed via context)

6. lib/api.ts:
   - API client מבוסס fetch עם טיפוסים
   - base URL מ-env (NEXT_PUBLIC_API_URL)
   - wrapper functions per endpoint (בלי שימוש ישיר ב-fetch בשאר הקוד)
   - error handling עקבי - throws APIError עם status + message
   - ללא auth עדיין (נוסיף בהמשך אם צריך)

7. lib/types.ts:
   - Shared types - מקבילים ל-Pydantic models של ה-backend:
     * Incident, IncidentStatus, Category
     * InvestigationResult, Evidence, SuggestedAction
     * ToolExecution
     * EnrichmentContext, SimilarIncident
     * ActionMetric, HostStatistics, Pattern
   - אידיאלי: generate אוטומטית מ-OpenAPI spec (הציע setup של openapi-typescript)

8. hooks/useIncidents.ts, useIncident.ts, useMetrics.ts:
   - TanStack Query hooks עם keys מסודרים
   - refetch interval נמוך + WebSocket live updates
   - optimistic updates היכן שצריך

9. components/ui/* - shadcn בסיסיים
   components/layout/Sidebar.tsx, TopBar.tsx
   components/common/ConnectionStatus.tsx
   components/common/SeverityBadge.tsx
   components/common/CategoryBadge.tsx
   components/common/ConfidenceBar.tsx
   components/common/RelativeTime.tsx (time ago)

10. styles/globals.css:
    - CSS variables לdark & light (pairs)
    - טוקנים: --color-critical, --color-warning, --color-investigating, 
      --color-resolved, --color-info
    - מיפוי ל-Tailwind תחת theme extend

11. Placeholder pages:
    - /live → "Live Operations coming in stage 09"
    - /incidents/[id] → "Deep Dive coming in stage 10"
    - /performance → placeholder
    - /knowledge → placeholder

12. docker-compose.override.yml (optional) לdev:
    - frontend container (Next.js dev)
    - hot reload works

13. README.md בשורש frontend:
    - איך להריץ dev
    - איך לבנות production
    - איך להוסיף shadcn component חדש
    - איך לחבר ל-backend (env vars)

דגשים:
- Dark mode **נבנה נכון**: צבעים דרך CSS vars, לא hard-coded. בוחן: מעבר 
  לlight יעבוד בלי שינוי קוד.
- Font loading: להשתמש ב-next/font כדי להמנע מ-layout shift
- Server components by default. Client components רק להתנהגות (useState, 
  useEffect, onClick)
- Typography: technical IDs/hostnames במונוסapce, הכל אחר בsans
- Dense but readable: space בין sections, לא בתוך

שאלות להבהיר:
- האם יש design system קיים בארגון (צבעים, לוגו)?
- האם הוא נדרש להיות RTL? (עברית/ערבית) - כרגע התשתית תומכת, אבל מציג בעיקר 
  טקסט טכני באנגלית
- האם יש auth (SSO, OIDC)? אם כן, אצטרך לשלב middleware

התחל ב-setup, אחר כך layout, אחר כך providers ו-hooks, אחר כך placeholder pages.
```

---

## CHECKLIST

- [ ] `npm run dev` עולה בלי שגיאות
- [ ] 4 מסכים placeholder נגישים
- [ ] Sidebar navigation עובד
- [ ] Dark/light toggle עובד ועקבי
- [ ] WebSocket מתחבר לbackend ומראה status
- [ ] TanStack Query hooks עובדים (test עם /health)
- [ ] Types סנכרוניים לbackend

## פלט צפוי

מסגרת frontend מוכנה לכל המסכים. כל שלב עוקב בונה רק את המסך הספציפי שלו.
