# Stage 03 - Triage Layer (Fingerprint, Dedup, Correlate, Classify)

## מטרת השלב

לבנות את שכבת המיון שמונעת רעש מההתחלה. alert storm של 50 שרתים לא יוצר 50 
investigations - הוא יוצר אירוע אחד מקובץ. זה המגן של כל המערכת מפני עומס, 
עלויות LLM מיותרות, ו-alert fatigue של הצוות.

## הקשר מוקדם

ראה `CLAUDE.md`.
שלבים 01 (Foundation) ו-02 (Tool Registry) הושלמו.

---

## PROMPT (להעברה ל-Claude)

```
אני עובד על פרויקט NOC Agent שמתואר ב-CLAUDE.md. השלבים 01 (Foundation) ו-02 
(Tool Registry) הושלמו.

בסשן הזה אני בונה את שכבת ה-Triage - הדבר הראשון שקורה אחרי שה-webhook מקבל 
alert. זה קריטי למנוע alert storms מלהפיל את המערכת.

דרישות:

1. app/services/triage/fingerprint.py:
   - compute_fingerprint(alert: GrafanaAlert) -> str
   - לוקח: alert_name, hostname, metric cluster (לא הערך עצמו!), time_window_5min
   - מחזיר hash יציב (SHA256 hex)
   - חשוב: alerts דומים שמגיעים בזה אחר זה בחלון של 5 דקות יקבלו אותו fingerprint
   - בדיקות: שנות time_window לא משנה את ה-hash באותה דקה; שינוי host כן משנה

2. app/services/triage/dedup.py:
   - DedupService class
   - async def check_duplicate(fingerprint: str, window_minutes: int = 15) -> 
     Incident | None
   - משתמש ב-Redis SET עם TTL לזיהוי מהיר
   - fallback ל-DB query אם Redis נופל
   - אם נמצא duplicate: מעלה counter על ה-incident הקיים, מוסיף event ל-timeline
   - נחזיר את ה-incident הקיים אם duplicate

3. app/services/triage/correlation.py:
   - CorrelationService
   - async def find_related_incidents(incident: Incident, window_minutes: int = 10) 
     -> list[Incident]
   - קורלציה לפי:
     * זמן (חלון של 10 דקות)
     * אותו datacenter / rack / switch (לפי labels)
     * קטגוריה זהה
     * metric cluster דומה
   - אם מוצא 3+ incidents דומים במקביל: מציע לקבץ לparent incident
   - הקיבוץ עצמו: יוצר parent incident, מקשר את ה-children
   - שמור score של confidence לקבוצה

4. app/services/triage/classifier.py:
   - ClassificationService
   - async def classify(alert: GrafanaAlert) -> Category
   - סיווג לאחת משלוש הקטגוריות:
     * physical (CPU, memory, disk, IO, temperature, network interface stats)
     * data_integrity (freshness, gaps, pipeline lag, missing records)
     * coupling (link status, peering, session health, BGP)
   - שיטה: rule-based (labels + alertname patterns) עם fallback ל-manual_review 
     אם לא ברור
   - מפת rules ב-config, ניתנת להרחבה בלי code change
   - logged decision עם reason (לאודיט)

5. app/services/triage/pipeline.py:
   - TriagePipeline - orchestrator
   - async def run(alert: GrafanaAlert) -> TriageResult
   - שלבים:
     1. fingerprint
     2. dedup check → אם duplicate: עדכן + return
     3. classify → אם manual_review: flag
     4. find_related → אם יש קבוצה: merge או parent
     5. persist incident עם כל ה-metadata
     6. publish event ל-Redis (ל-UI live updates)
   - מחזיר TriageResult עם: action taken, incident_id, was_duplicate, was_grouped

6. app/api/webhooks.py - עדכון:
   - אחרי שה-alert נשמר, להריץ TriagePipeline
   - כל העבודה מה-pipeline קורית בtrailer: הפונקציה מחזירה 202 מיד, ה-pipeline 
     רץ ב-BackgroundTasks או Redis queue
   - החלטה: אם הצפי לעומס גבוה - queue. אם לא - BackgroundTasks זה מספיק לעת 
     עתה. שאל את המשתמש מה הצפי.

7. tests/services/test_triage.py:
   - fingerprint: יציבות, הבדלים נכונים
   - dedup: alert חוזר מאותה fingerprint - מזוהה; alert שונה - לא
   - correlation: 5 alerts באותו DC תוך דקה - מקובצים
   - classifier: כל קטגוריה מסווגת נכון; edge case נופל ל-manual_review
   - pipeline end-to-end עם mock redis + real postgres (testcontainers)

8. app/core/config.py - תוספות:
   - TRIAGE_DEDUP_WINDOW_MINUTES (default 15)
   - TRIAGE_CORRELATION_WINDOW_MINUTES (default 10)
   - TRIAGE_CORRELATION_MIN_GROUP_SIZE (default 3)
   - TRIAGE_CLASSIFICATION_RULES_PATH (path ל-YAML של rules)

9. config/classification_rules.yaml - דוגמה ראשונית:
   - rules per category: patterns של alertname, required labels, metric hints
   - סדר: מהספציפי לכללי
   - דוגמה מלאה עם 5-10 rules לכל קטגוריה

דגשים:
- Logging עם context מלא בכל צעד: alert_id, incident_id, category, fingerprint
- כל החלטה (duplicate, group, classify) נשמרת עם timestamp + reason לאודיט
- Redis failure אסור להפיל את ה-pipeline - fallback ל-DB
- Rules ב-YAML כדי שאפשר לעדכן בלי deploy

שאלות שאשמח להבהיר:
- מה הצפי לעומס? (alerts per minute בימי שגרה + ב-incident major)
- האם יש labels סטנדרטיים מGrafana שלך שאני יכול להניח קיימים (datacenter, rack, 
  service)? אם כן, אילו?
- האם יש classification pattern קיים אצלך שאני יכול לבנות עליו?

התחל בהצגת flow diagram (טקסטואלי) של ה-pipeline, ואז קבצים לפי הסדר.
```

---

## CHECKLIST

- [ ] fingerprint יציב וייחודי
- [ ] dedup ב-Redis עם TTL עובד
- [ ] correlation מזהה קבוצות (3+ דומים) ומקבץ
- [ ] classifier מחזיר נכון לכל קטגוריה; unknown → manual_review
- [ ] webhook מריץ את ה-pipeline בלי לחסום את ה-response
- [ ] כל החלטה נשמרת ב-DB עם reason
- [ ] tests עוברים כולל integration
- [ ] YAML rules נטענים ב-startup וניתנים לרענון

## פלט צפוי

מערכת שמקבלת alerts ומסננת רעש. גם אם 100 שרתים נופלים באותה דקה - נקבל 1-2 
parent incidents במקום 100.

## טיפים להמשך

- אחרי שזה עובד, שווה להוסיף metrics ל-Prometheus: dedup_rate, correlation_rate, 
  classification_distribution, manual_review_queue_size. אלה יהיו המטריקות 
  הכי חשובות שלך בחודש הראשון.
