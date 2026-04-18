# Stage 06 - Jira Integration + Structured Tickets + Custom Fields

## מטרת השלב

לבנות ממשק Jira דו-כיווני עם מבנה ticket קשיח ושדות feedback חובה. ה-tickets 
שהמערכת פותחת צריכים להיות קריאים, פעולתיים, וכאלה שמאפשרים ללמוד מהם.

**זה השלב שבונה את התשתית ל-feedback loop.**

## הקשר מוקדם

ראה `CLAUDE.md`.
שלבים 01-05 הושלמו. יש investigator agent שמייצר InvestigationResult מובנה.

---

## PROMPT (להעברה ל-Claude)

```
אני עובד על פרויקט NOC Agent שמתואר ב-CLAUDE.md. שלבים 01-05 הושלמו - יש 
מערכת מלאה שמקבלת alerts, חוקרת, ומייצרת InvestigationResult.

בסשן הזה אני בונה את Jira Integration - גם את פתיחת ה-tickets וגם את ה-sync 
חזרה כשמשהו נסגר. השדות המובנים כאן הם התשתית ל-feedback loop בשלב הבא.

דרישות:

1. Jira Setup (guidance למשתמש):
   - doc בתיקיית ה-repo: docs/jira_setup.md
   - צעדים שהמשתמש צריך לעשות ידנית ב-Jira:
     * יצירת project / issue type ("NOC Alert")
     * יצירת custom fields:
       - incident_id (text)
       - category (select: physical/data_integrity/coupling)
       - fingerprint (text, indexed)
       - confidence (number)
       - suggested_action (text)
       - hypothesis (text, multi-line)
       - resolution_category (select, from our list)
       - was_hypothesis_correct (select: yes/partially/no)
       - actual_resolution_details (text, multi-line)
       - resolution_time_minutes (number, auto-calculated)
     * workflow states: Open → Investigating → Resolved → Closed
     * automation rule: webhook to our system on transition to Resolved
   - screenshots תיאוריים של איך עושים את זה (placeholder paths)

2. app/services/jira/client.py:
   - JiraClient class (אסינכרוני עם httpx)
   - auth: Basic Auth עם email + API token (מ-config)
   - methods:
     * async def create_issue(...) -> JiraIssue
     * async def update_issue(issue_key, fields) -> None
     * async def add_comment(issue_key, body) -> None
     * async def transition_issue(issue_key, transition_name) -> None
     * async def get_issue(issue_key) -> JiraIssue
   - retries עם tenacity (exponential backoff על 5xx)
   - rate limiting (httpx limits + custom semaphore אם צריך)

3. app/services/jira/templates.py:
   - build_ticket_content(incident, investigation) -> JiraTicketContent
   - מבנה הtiket:
     * Title: `[AUTO] {severity} - {short_hypothesis} on {hostname}`
     * Description (markdown, Jira format):
       - TL;DR (שורה אחת)
       - Timeline (התראה, התחלת חקירה, סיום)
       - Evidence Summary (bullet points מה-evidence_chain)
       - Hypothesis (עם confidence bar ויזואלי ב-text)
       - Suggested Action (בלט גדול)
       - Alternatives Considered (קצר, מסבירים למה נפסלו)
       - Historical Context (similar incidents מה-IKB)
       - Correlation (אם קיימים related incidents)
       - --- separator ---
       - Resolution Section (מתבקש מילוי):
         * Actual resolution category: [dropdown placeholder]
         * Was hypothesis correct?: [yes/partially/no]
         * Actual action taken: [text]
   - שמירת ה-template מובנה כך שכל ticket נראה אותו דבר

4. app/services/jira/ticket_creator.py:
   - TicketCreator
   - async def create_from_investigation(
         incident: Incident, 
         investigation: InvestigationResult
     ) -> TicketRef
   - שלבים:
     1. בניית ה-content
     2. קריאה ל-JiraClient.create_issue
     3. שמירת ה-issue_key ב-incident (עדכון DB)
     4. emit event (Redis pubsub) לUI
   - טיפול בכשלונות: אם Jira לא זמין, incident נשמר עם status "ticket_pending" 
     ו-retry job ירוץ אחר כך (APScheduler או Redis delayed queue)

5. app/api/webhooks.py - תוספת:
   - POST /webhooks/jira - מקבל notifications מ-Jira
   - validation של HMAC signature (אם Jira תומך, או IP allowlist)
   - events שמעניינים אותנו:
     * issue updated (resolution fields)
     * issue transitioned to Resolved
   - כל event → dispatch ל-JiraSyncHandler

6. app/services/jira/sync_handler.py:
   - JiraSyncHandler
   - async def handle_resolution(issue_key, resolved_fields) -> None
   - שלבים:
     1. מציאת ה-incident לפי issue_key
     2. validation ששדות ה-resolution מולאו (חובה!)
     3. עדכון ה-incident: resolution_category, was_hypothesis_correct, 
        actual_resolution_details, resolution_time_minutes
     4. חישוב resolution_time (מ-incident.created_at ועד עכשיו)
     5. trigger שלב הפידבק: update embeddings, update action metrics, 
        baseline considerations (זה קורה בשלב 07)
   - emit event (Redis pubsub) לUI

7. app/services/jira/polling_fallback.py:
   - fallback אם webhook לא אמין
   - job כל 5 דקות: שולף issues שעברו ל-Resolved ב-15 הדקות האחרונות
   - מריץ עליהם JiraSyncHandler (idempotent - שלא ישכפל)

8. tests:
   - JiraClient עם mock responses (respx או httpx_mock)
   - Ticket rendering - snapshot test של template
   - Ticket creation end-to-end
   - Sync handler: validation נכונה, עדכון DB
   - Rate limiting עובד

9. app/core/config.py - תוספות:
   - JIRA_URL (e.g. https://mycompany.atlassian.net)
   - JIRA_EMAIL
   - JIRA_API_TOKEN
   - JIRA_PROJECT_KEY (e.g. "NOC")
   - JIRA_ISSUE_TYPE (e.g. "NOC Alert")
   - JIRA_WEBHOOK_SECRET (אם קיים)
   - JIRA_CUSTOM_FIELD_IDS (dict mapping שמות שלנו למזהי custom fields - 
     זה משתנה בין תקנות Jira)

דגשים:
- Jira custom fields IDs (customfield_10XXX) שונים בכל instance. חשוב שה-config 
  יגדיר אותם במפורש.
- שדות ה-feedback חייבים להיות required ב-Jira לstatus transition ל-Resolved. 
  זה אוכף שהצוות ימלא.
- Markdown → Jira wiki markup יש להמיר (יש ספריות, או להשתמש בADF פורמט 
  החדש יותר של Atlassian).
- ADF (Atlassian Document Format) מומלץ על פני markdown פשוט - יותר שליטה 
  על visual.
- Avoid spam: אם ticket כבר קיים עבור אותו parent incident (correlation), הוסף 
  comment במקום לפתוח חדש.

שאלות להבהיר:
- איזה Jira (Cloud/Server/Data Center)? זה משפיע על API
- האם יש אצלך Jira project כבר, או שצריך ליצור חדש?
- איזה authentication מומלץ? (API token, OAuth, Personal Access Token)
- האם אפשר ליצור custom fields (דורש הרשאות admin)?

התחל בתיעוד של הsetup הידני ב-Jira, אחר כך code.
```

---

## CHECKLIST

- [ ] Jira custom fields נוצרו ומוגדרים בconfig
- [ ] Ticket creation עובד end-to-end
- [ ] Ticket format מובנה ונראה טוב ב-Jira UI
- [ ] Webhook מ-Jira מתקבל ומטפל ב-resolution
- [ ] שדות feedback חובה ב-workflow transition
- [ ] Polling fallback פועל כ-backup
- [ ] Rate limiting ו-retries עובדים
- [ ] Tests עוברים

## פלט צפוי

לולאה מלאה: alert → investigation → ticket מובנה. וגם לולאה הפוכה: ticket 
סגור → עדכון DB עם resolution. **זו התשתית לפני ה-feedback loop.**

## הערה קריטית

**מהיום הראשון שהמערכת עולה לפרודקשן, שדות ה-feedback חייבים להיות חובה.** אם 
הצוות יכול לסגור ticket בלי למלא אותם, המערכת לא תלמד - ואי אפשר להוסיף את זה 
רטרואקטיבית. השקעה של שעה ב-Jira admin עכשיו שווה חודשים של data איכותי אחר כך.
