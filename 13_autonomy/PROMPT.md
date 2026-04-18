# Stage 13 - Graded Autonomous Remediation

## מטרת השלב

להפוך את המערכת מ-"מציעה" ל-"עושה" - אבל בזהירות. מדרג tiers של פעולות, עם 
כללי aufstieg מבוססי-מטריקות, shadow mode, kill switch, ו-audit trail מלא.

**השלב הזה מתחיל רק אחרי 2-3 חודשי feedback data מוצק.**

## הקשר מוקדם

ראה `CLAUDE.md`. כל השלבים הקודמים (01-12) הושלמו. יש מטריקות אמינות משמעותיות 
על action types.

---

## PROMPT (להעברה ל-Claude)

```
אני עובד על פרויקט NOC Agent שמתואר ב-CLAUDE.md. המערכת עובדת בפרודקשן כבר 
2-3 חודשים, יש דאטה אמין על action precision ו-hypothesis accuracy.

בסשן הזה אני בונה את המנגנון ל-autonomous remediation מדורג.

**עיקרון על:** פעולה autonomous היא האפשרות המסוכנת ביותר במערכת. כל guardrail 
כפול. בלי קיצורי דרך. יותר טוב שphone engineer יתעורר מאשר שהמערכת תפיל 
שרת בטעות.

Tier System:

Tier 0 - Always Automatic (from day 1):
- Non-destructive informational:
  * Add context comment to Jira ticket
  * Tag related incidents
  * Enrich ticket with similar historical incidents
  * Send notification to relevant team channel

Tier 1 - Autonomous with Gate (after reliability established):
- Safe operational actions:
  * Restart specific services (allowlist per service)
  * Clear specific caches
  * Acknowledge known maintenance windows
  * Mark as false positive (with high confidence threshold)
  * Gate requires: 200+ samples, 95%+ precision, 30-day streak, 
    0 false positives last 60 days

Tier 2 - Human Approval Required:
- Potentially impactful:
  * Restart services not in Tier 1 allowlist
  * Modify configs (specific allowed modifications only)
  * Drain traffic from node
  * Agent proposes action, UI shows "one-click approve" to on-call

Tier 3 - Manual Only (never automated):
- Destructive or complex:
  * Reboot host
  * Any hardware operation
  * Config changes outside allowed set
  * Scale operations

דרישות:

1. app/services/autonomy/tier_manager.py:
   - TierManager
   - async def evaluate_action_readiness(action_key: str) -> ReadinessReport
     * check metrics: precision, samples, streak, FP rate
     * compare to tier requirements in config
     * return eligible_tier, missing_requirements, recommendation
   - async def promote_action(action_key: str, new_tier: int, approver: str) 
     -> None
     * audit log entry
     * config update (DB-backed, not file)
     * emit event
   - async def demote_action(action_key: str, reason: str) -> None
     * automatic demotion if error detected
     * immediate effect

2. app/services/autonomy/executor.py:
   - AutonomousExecutor
   - async def maybe_execute(investigation: InvestigationResult) -> ExecutionDecision
     * check action tier
     * check confidence threshold
     * check global kill switch
     * check rate limiting (max X autonomous actions per hour)
     * if all clear: execute
     * else: create ticket for human review
   - execute() itself uses existing Tool system with safety_level="side_effects"
   - every autonomous execution:
     * pre-execution snapshot (state before)
     * execution
     * post-execution verification (state after + health check)
     * rollback если verification fails
     * audit log

3. app/services/autonomy/shadow_mode.py:
   - ShadowExecutor
   - כל action חדש ש-promotion מוצע לו עובר shadow mode קודם:
     * המערכת **היתה** מבצעת, אבל לא באמת
     * שומרת את ההחלטה ואת התוצאה הצפויה
     * engineer מאשר ידנית את האמיתי
     * אחרי X days בshadow mode עם 100% match - eligible לpromotion

4. app/services/autonomy/rollback.py:
   - RollbackService
   - כל autonomous action חייב rollback function
   - triggered if:
     * post-execution verification fails
     * incident severity increases within 5 minutes after action
     * human manually invokes rollback from UI
   - some actions irreversible - אלה לא מגיעים לTier 1

5. app/services/autonomy/circuit_breaker.py:
   - CircuitBreakerService
   - per action type, per host
   - if X failed autonomous executions within Y time → circuit opens
   - while open: no autonomous for this action/host combination
   - auto-reset after cooldown + manual reset option

6. Kill Switch (global):
   - config flag: AUTONOMY_ENABLED (default: false!)
   - UI button: "Stop All Autonomous" (admin only)
   - when off: all actions revert to "human approval required"
   - state persisted, survives restart

7. Audit Trail:
   - new table: autonomous_actions
     * id, action_key, incident_id, executed_at, executor_version, 
       pre_snapshot, post_snapshot, verification_result, rollback_triggered, 
       rolled_back_at, operator_notes
   - every row immutable (append-only)
   - easily queryable for incident post-mortems

8. UI changes:
   - Live Operations: badge on incident if autonomous action was taken
   - Incident Detail: "Autonomous Action" section showing full audit
   - New page: /autonomy
     * Current tier assignment per action
     * Recent autonomous executions
     * Kill switch
     * Manual rollback trigger
     * Shadow mode queue
   - Performance Dashboard:
     * "Actions by tier" chart
     * Autonomous action success rate
     * Time saved estimate

9. Alerting:
   - if autonomous action fails verification → page on-call
   - if rollback triggered → page on-call
   - if circuit breaker opens → notify team (not page)
   - if kill switch activated → log + notify management

10. Rate limiting:
    - max 10 autonomous actions per minute system-wide
    - max 3 per host per hour (prevent cascading)
    - per-action-type limits configurable

11. Tests (critical):
    - Tier gate enforcement
    - Shadow mode: decisions match but don't execute
    - Kill switch: no action regardless of gate
    - Rollback triggers correctly
    - Circuit breaker: opens/closes properly
    - Audit trail complete and immutable
    - Rate limiting works

12. Runbook (docs/autonomy_runbook.md):
    - מה לעשות כש-autonomous action נכשל
    - איך לעשות manual rollback
    - איך לכבות autonomy במקרה חרום
    - מתי להעלות action לTier גבוה יותר (decision framework)
    - איך לחקור false positive autonomous action

עיקריים של זהירות:
- **Default = everything off**. Autonomy מופעל per-action, per-host, after 
  explicit admin decision עם evidence.
- **Shadow mode לפחות 14 יום** לפני Tier 1. אין קיצור דרך.
- **Verification אחרי כל execution** - השרת באמת חזר לנורמלי?
- **Rollback חייב להיות bulletproof** - tested in non-prod first.
- **Audit trail immutable** - never delete autonomous_actions records.

שאלות להבהיר:
- מי מאשר promotion ל-Tier 1 - אתה לבד או דורש approval מ-infra team?
- Alerting: PagerDuty / Opsgenie / email / Slack?
- יש כבר deployment safety practices בצוות? (change freeze windows, etc.)

**זה השלב שבו אסור לקצר.** התחל בtier_manager + audit trail + kill switch. 
רק אחרי שהם יציבים עוברים ל-executor. ובאמת: אל תפעיל autonomy אלא אחרי 
2-3 חודשים של data + shadow mode מלא.
```

---

## CHECKLIST

- [ ] Tier system מוגדר עם config ברור
- [ ] Tier gate נאכף (metrics thresholds)
- [ ] Shadow mode פועל ומאסף decisions ל-comparison
- [ ] Kill switch עובד ומיידי
- [ ] Audit trail שלם לכל action
- [ ] Rollback tested
- [ ] Circuit breaker עובד
- [ ] Rate limiting
- [ ] UI מציג autonomy state
- [ ] Runbook כתוב

## פלט צפוי

מערכת שיכולה לטפל אוטונומית בחלק גדול מההתראות, בצורה בטוחה, עם safety nets 
מרובים. הצוות מתמקד ב-incidents מורכבים; המערכת מטפלת בשגרה.

## הערה אישית לעצמך בעתיד

כשתרצה להאיץ ולקצר guardrails - עצור. **מעולם לא התחרטתי על being too careful 
with autonomy; תמיד התחרטתי על being too aggressive.** המערכת שלך תתמוך במאות 
שרתים; incident אחד גדול שנגרם ע"י autonomous action רע יעלה יותר מכל השעות 
שנחסכו.
