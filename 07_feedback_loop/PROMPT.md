# Stage 07 - Feedback Loop (Learning from Resolutions)

## מטרת השלב

לסגור את המעגל: כשticket נסגר עם resolution, המערכת לומדת. Embeddings מחודשים 
מחדש, מטריקות איכות מתעדכנות, דפוסים מזוהים. **זה השלב שבלעדיו כל היתר לא שווה.**

## הקשר מוקדם

ראה `CLAUDE.md`.
שלבים 01-06 הושלמו. יש jira sync handler שמקבל resolution data - עכשיו 
אנחנו מפעילים אותה.

---

## PROMPT (להעברה ל-Claude)

```
אני עובד על פרויקט NOC Agent שמתואר ב-CLAUDE.md. שלבים 01-06 הושלמו. יש 
מערכת מלאה שמקבלת resolution data מ-Jira ומעדכנת את ה-incident ב-DB.

בסשן הזה אני בונה את ה-Feedback Loop - מה קורה אחרי שה-resolution נכנסה. 
המטרה: כל ticket סגור מעשיר את המערכת כך שה-investigation הבאה תהיה טובה יותר.

דרישות:

1. app/services/feedback/orchestrator.py:
   - FeedbackOrchestrator
   - async def process_resolution(incident_id: UUID) -> None
   - נקרא אחרי ש-JiraSyncHandler עדכן את ה-resolution
   - מריץ במקביל (asyncio.gather):
     1. re_embed_incident
     2. update_action_metrics
     3. update_host_statistics
     4. detect_recurrence
     5. update_baselines_hint
     6. emit_feedback_events
   - logging מפורט לכל שלב

2. app/services/feedback/re_embedding.py:
   - async def re_embed_incident(incident_id) -> None
   - לוקח את ה-incident עם resolution מלא
   - מחשב embedding חדש עם הטקסט העשיר (כולל resolution_category, actual 
     resolution details, correctness flag)
   - מעדכן את שדה ה-embedding ב-DB
   - זה חשוב: עכשיו chapter similarity search עתידי ימצא את ה-incident עם 
     כל הידע

3. app/services/feedback/action_metrics.py:
   - ActionMetricsService
   - טבלה חדשה: action_metrics (מתווסף ב-migration):
     * action_key (FK to allowlist)
     * total_suggested (int)
     * total_approved (int)  -- צוות אישר את ההצעה
     * total_executed (int)  -- בוצע בפועל (גם אם modified)
     * total_hypothesis_correct (int)
     * total_hypothesis_partially (int)
     * total_hypothesis_wrong (int)
     * avg_resolution_time_minutes (float)
     * last_updated (timestamp)
     * streak_days_without_error (int)  -- חשוב ל-autonomy tier promotion
     * last_error_at (timestamp | null)
   - async def update_from_resolution(incident) -> None
     * increment counters
     * אם was_hypothesis_correct='no': reset streak, set last_error_at
     * אם correct/partial: increment streak

4. app/services/feedback/host_statistics.py:
   - async def update_host_statistics(hostname) -> None
   - טבלה: host_statistics
     * hostname (PK)
     * total_incidents
     * incidents_last_30d, incidents_last_7d
     * most_common_resolution_category
     * avg_resolution_time
     * last_incident_at
     * is_recurring_problem (bool) - flag אם יש הרבה incidents תדיר
   - חישוב מחדש אחרי כל incident שנסגר (lightweight, אגרגציה על incidents 
     של ה-host)

5. app/services/feedback/recurrence_detector.py:
   - async def detect_recurrence(incident) -> RecurrenceInfo | None
   - בודק: האם קיימים incidents דומים (לפי embedding similarity + זמן) על 
     אותו host ב-90 ימים אחרונים?
   - אם כן:
     * מעדכן incident.recurrence_count
     * יוצר עבורו "recurrence alert" - התראה פנימית שצריך לטפל באופן מערכתי
     * אם recurrence_count > 5: escalate flag על ה-host
   - מחזיר RecurrenceInfo עם: count, first_seen, previous_resolutions, 
     pattern_description

6. app/services/feedback/pattern_detector.py:
   - זה קצת שונה - רץ לא אחרי כל resolution אלא בסוף יום/שבוע
   - async def detect_patterns_weekly() -> list[Pattern]
   - מזהה:
     * hosts עם עלייה בincident rate (compare last 7d to prior 30d avg)
     * resolution categories שחוזרות על עצמן בצורה חשודה
     * alert types חדשים שלא ראינו לפני החודש האחרון
     * hypothesis accuracy יורד בקטגוריה מסוימת
   - יוצר dashboard_alerts table לתצוגה ב-UI (מסך 11)

7. app/services/feedback/events.py:
   - emit_feedback_events - ל-Redis pubsub
   - events:
     * incident.resolved - לUI לעדכן רשימת live
     * metrics.updated - לdashboard לרענן
     * recurrence.detected - notification לצוות
     * pattern.detected - weekly report

8. app/tasks/feedback_jobs.py:
   - APScheduler jobs:
     * daily_host_statistics_refresh (רץ ב-2AM)
     * weekly_pattern_detection (Sunday 3AM)
     * monthly_action_metrics_cleanup (בדיקה שאין outliers)

9. app/api/feedback.py - endpoints:
   - GET /metrics/actions - קבלת action_metrics לטבלה
   - GET /metrics/hosts/{hostname} - host statistics
   - GET /patterns/recent - דפוסים שזוהו לאחרונה
   - GET /recurrence/active - hosts עם recurring problems

10. tests:
    - re-embedding: embedding חדש שונה מהישן ועשיר יותר
    - action_metrics: עדכונים נכונים לפי correctness
    - recurrence detection מוצא incidents קודמים
    - pattern detector מזהה spikes מלאכותיים
    - all feedback pipeline end-to-end (mock jira resolution → verify all 
      side effects)

11. Observability additions:
    - Prometheus counters:
      * incidents_resolved_total{category, correct}
      * hypothesis_accuracy_rate (derived)
      * recurrence_detected_total
    - Grafana dashboard template (JSON): "NOC Agent Quality"
      * hypothesis accuracy over time
      * action approval rates
      * recurrence rate
      * cost per resolved incident

דגשים:
- **Idempotency חשובה**. אם resolution נקרא פעמיים (webhook + polling), 
  הכל חייב לעבוד נכון. השתמש ב-processed_resolution_events table עם 
  idempotency_key.
- re-embedding עולה כסף (אם openai/anthropic). שקול batch אחרי יום במקום 
  מיד, או local model ל-re-embedding.
- מטריקות ה-action זה הדלק של autonomy decision - תעד את כל החלטה 
  עם evidence מלא.
- אל תצור loops אם event handling מעורר עוד events. pubsub משמש להודעה, 
  לא ל-chaining.

שאלות להבהיר:
- האם יש תהליך קיים של post-mortem בצוות שאפשר להתחבר אליו?
- מי מעוניין ב-pattern reports השבועיים? (מי מקבל את ההודעה?)
- האם אתה רוצה thresholds מגוונים לrecurrence (למשל high-severity: 2 
  incidents; low-severity: 5)?

התחל בdata models של המטריקות, אחר כך orchestrator, אחר כך הרכיבים.
```

---

## CHECKLIST

- [ ] כל resolution גורמת ל-re-embedding
- [ ] action_metrics מתעדכנות נכון (correct/partial/wrong)
- [ ] host_statistics מתעדכנות
- [ ] recurrence מזוהה ומתריע
- [ ] pattern detector רץ שבועית ומייצר reports
- [ ] Idempotency: שני events זהים לא גורמים לעדכון כפול
- [ ] Prometheus metrics מיוצאים
- [ ] Grafana dashboard עובד

## פלט צפוי

המערכת **לומדת**. כל תקלה שנסגרת הופכת אותה חכמה יותר. מטריקות האיכות מתחילות 
להצטבר - אלה יהיו הנתונים שעליהם תתבסס ההחלטה לעבור ל-autonomy.

## נקודת חסימה אפשרית

אם שדות ה-feedback ב-Jira לא מולאו (או מולאו חלקית), כל ה-pipeline הזה לא 
מקבל דלק. לכן **השדות הם required ב-Jira** (שלב 06), ובנוסף ה-FeedbackOrchestrator 
חייב לדעת לטפל נכון ב-partial data (לוג warning, לא fail).

**אחרי השלב הזה, המערכת מוכנה ל-UI.**
