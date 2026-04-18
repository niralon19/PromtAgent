# Stage 10 - Incident Deep Dive Screen

## מטרת השלב

**המסך הכי חשוב במערכת.** כאן engineer מחליט האם לסמוך על הסוכן או לא. שקיפות 
מלאה של ה-investigation: timeline של כלים שרצו, evidence chain, hypothesis 
עם alternatives, context מ-IKB, ו-actions חד-קליק.

## הקשר מוקדם

ראה `CLAUDE.md`. שלב 09 (Live Operations) הושלם.

---

## PROMPT (להעברה ל-Claude)

```
אני עובד על פרויקט NOC Agent שמתואר ב-CLAUDE.md. שלב 09 (Live Operations) 
הושלם.

בסשן הזה אני בונה את המסך הקריטי ביותר: Incident Deep Dive. כאן בני אדם 
מחליטים האם לסמוך על ההמלצות של המערכת. שקיפות מלאה, reasoning חשוף, 
evidence נגיש.

Layout: 3 עמודות.

דרישות:

1. app/(dashboard)/incidents/[id]/page.tsx:
   - Server component שטוען את ה-incident המלא עם כל ה-enrichment
   - SSR initial, client updates דרך WebSocket לlive investigation

2. Layout - 3 columns (Grid):
   - Left (30%): Investigation Timeline
   - Center (40%): Analysis
   - Right (30%): IKB Context
   - Sticky header למעלה: title + severity + host + actions bar
   - Responsive: בmobile נעבור ל-tabs במקום columns

3. components/incident/Header.tsx:
   - Title: `${hostname} - ${alertname}` - monospace לhost
   - Severity badge גדול
   - Category badge
   - Age + status
   - Breadcrumb: Live > Incident #XXX
   - Right side: action buttons (Approve, Modify, Escalate, False Positive, 
     Close)

4. components/incident/timeline/InvestigationTimeline.tsx (LEFT):
   - Vertical timeline, כל item = step בinvestigation
   - Items:
     * Alert received
     * Triage decisions (classification, dedup check, correlation)
     * Enrichment loaded (similar incidents found)
     * Tool execution (expandable - click to see input/output)
     * Agent reasoning steps (expandable - show LLM reasoning)
     * Hypothesis formed
     * Ticket created
   - כל item: icon (tool/agent/trigger), timestamp, short description, 
     expandable raw data
   - Live update: אם investigation עדיין פעיל, spinner + נוסף items בזמן אמת

5. components/incident/analysis/AnalysisPanel.tsx (CENTER):
   - Hypothesis card:
     * Large text של ה-hypothesis
     * Confidence bar (0-100) עם צבע + label
     * Confidence rationale (why this level)
   - Evidence Chain card:
     * list of evidence, each linked to a tool execution
     * click → scroll timeline to that tool + highlight
   - Alternatives Considered card:
     * רשימה של alternative hypotheses שנפסלו
     * לכל אחד: sentence למה נפסל
     * זה מה שבונה אמון!
   - Suggested Action card:
     * Action name + description
     * Tier + whether approval required
     * Big "Approve & Execute" button (אם בtier 1+)
     * "Modify" opens editor
     * "Reject" requires reason

6. components/incident/context/IKBContextPanel.tsx (RIGHT):
   - Similar Incidents cards (5 top):
     * לכל אחד: date, hostname, resolution summary, similarity %
     * click → modal עם פרטי ה-incident הקודם
   - Host History chart:
     * Timeline של incidents על ה-host ב-90 ימים אחרונים
     * Bar chart או heatmap
   - Baseline Comparison chart:
     * מטריקת ה-alert עם baseline (mean + p95 bands)
     * Highlight של ה-alert point
     * Z-score + anomaly indicator
   - Related Active Incidents:
     * אם יש correlation - כרטיסיות של incidents קשורים
     * click → ניווט

7. components/incident/ActionBar.tsx (BOTTOM):
   - Actions:
     * Approve & Execute (אם autonomous available)
     * Approve & Log Only
     * Modify Suggested Action (dialog)
     * Escalate (dialog לבחירת tier/team)
     * Mark False Positive (confirm)
     * Close without Action
   - Feedback capture (נדרש לפני close):
     * Was hypothesis correct? [Yes] [Partially] [No] big buttons
     * Quick resolution note input
     * מעביר ל-Jira + לDB

8. components/incident/agent/AgentReasoning.tsx:
   - Inline בtimeline, expandable
   - מציג את ה-raw LLM output: thinking, tool_use decisions, synthesis
   - מוסתר by default, button "Show agent reasoning" לחשיפה
   - syntax highlighting לkod snippets
   - copy button לכל section

9. WebSocket subscriptions:
   - incidents.{id}.* - כל events על ה-incident הזה
   - investigation progress, tool executions, agent steps

10. Modal components:
    - ModifyActionDialog
    - EscalateDialog
    - SimilarIncidentModal
    - ToolExecutionDetailsModal

11. Tests:
    - Load incident → כל החלקים נטענים
    - Expand tool execution → פרטים מופיעים
    - Click similar incident → modal נפתח
    - Approve action → POST נשלח + optimistic update
    - Close with feedback → feedback נשמר

דגשים מיוחדים:
- **Explainability is everything**. כל החלטה של ה-agent חייבת להיות clickable 
  להסבר. "85% confidence" - click להסבר. "Hypothesis: X" - click ל-evidence. 
  זה בונה אמון.
- **"Alternatives Considered" visually prominent** - זה מה שמבדיל between 
  "AI מקריא תוצאות" ל-"AI חושב כמו mengineer". אל תצמצם את זה.
- Timeline density: 20-30 items זה נפוץ. חייב להיות דחוס אבל ברור.
- Live investigation: אם ה-agent עדיין רץ, ה-timeline מתעדכן ב-realtime. 
  זו חוויה שבונה אמון.
- Charts: dark mode נקי, בלי טקסטורות מיותרות. Tremor או Recharts עם 
  theme מותאם.

שאלות להבהיר:
- איזה data יש כבר ב-incident endpoint? צריך לוודא שה-API מחזיר הכל 
  ב-request אחד (עם includes/expand).
- האם Modal לsimilar incident צריך לטעון עוד דאטה, או מה שיש מספיק?

התחל ב-layout ובהצגת המידע הסטטי, אחר כך interactions, אחר כך live updates.
```

---

## CHECKLIST

- [ ] 3-column layout עובד ונראה טוב בdesktop
- [ ] Mobile: tabs במקום columns
- [ ] Timeline מציג את כל ה-steps עם expandable details
- [ ] Analysis panel מראה hypothesis, evidence, alternatives
- [ ] IKB panel מראה similar incidents + host history + baselines
- [ ] Action bar עובד עם כל ה-actions
- [ ] Feedback capture חובה לפני close
- [ ] Live updates כשה-investigation רץ
- [ ] כל interaction inside cards ברור ו-responsive

## פלט צפוי

**המסך שעושה או שובר את אמון הצוות.** אם המסך הזה טוב, הצוות יסמוך על המערכת 
ויתחיל להשתמש בה יומיומית. אם הוא לא ברור - הצוות יתעלם.
