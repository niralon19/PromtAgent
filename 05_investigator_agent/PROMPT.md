# Stage 05 - Investigator Agent (Anthropic SDK, Tool Use Loop)

## מטרת השלב

להפוך את ה-investigator מ-passive summarizer ל-active agent. במקום לקבל פלטים 
של כלים ולסכם, הוא יבחר דינמית אילו כלים להריץ על סמך מה שגילה, יבנה hypothesis 
מבוססת evidence, וייצר confidence מכויל.

**זה המוח של המערכת.**

## הקשר מוקדם

ראה `CLAUDE.md`.
שלבים 01-04 הושלמו. יש Tool Registry עובד, triage, ו-IKB עם enrichment.

---

## PROMPT (להעברה ל-Claude)

```
אני עובד על פרויקט NOC Agent שמתואר ב-CLAUDE.md. שלבים 01-04 הושלמו - יש 
scaffolding, tool registry, triage, ו-IKB עם embeddings + baselines.

בסשן הזה אני בונה את ה-Investigator Agent שהוא הלב של המערכת. ה-agent מקבל 
incident עם enrichment context, ומריץ לולאת חקירה דינמית באמצעות Anthropic 
tool use API.

**הערה קריטית**: החלטנו לזנוח CrewAI ולעבוד ישירות עם Anthropic SDK. הסיבות: 
שליטה מלאה על הלולאה, observability, עלות, וההכרה שאין אצלנו dialog בין 
agents (כל agent עצמאי).

דרישות:

1. app/services/agent/checklists.py:
   - CategoryChecklist class
   - dict של checklists לכל קטגוריה:
     * physical: ["מה המשאב הבעייתי?", "מה צורך אותו?", "מתי התחיל?", "האם עדיין 
       פעיל?", "האם יש דפוס היסטורי?"]
     * data_integrity: ["איפה הנתונים נעצרים?", "האם המקור שולח?", "מתי ראינו 
       נתונים אחרונים?", "האם יש שגיאות ב-pipeline?", "האם זו תקלת source או sink?"]
     * coupling: ["איזה צד נפל?", "כמה זמן?", "האם יש devices קרובים עם אותה 
       בעיה?", "האם יש תחזוקה מתוכננת?", "האם ה-neighbor מוכר?"]
   - כל פריט ב-checklist: {question, answered: bool, answer_evidence: list}
   - method: is_complete() -> bool
   - method: next_unanswered() -> str | None

2. app/services/agent/prompts.py:
   - build_system_prompt(category, checklist) -> str
   - הוראות ברורות ל-agent:
     * מי אתה (senior NOC engineer investigating an incident)
     * מה המטרה (answer the checklist questions using available tools)
     * איך לחשוב (step by step, state what's known/unknown, cite evidence)
     * מה החובה להפיק (hypothesis, confidence 0-100, suggested_action, 
       evidence_chain, alternatives_considered)
     * עקרונות (confidence = calibrated probability; high only with converging 
       evidence; say "unknown" when unknown)
   - build_user_message(incident, enrichment) -> str
     * מציג את ה-alert, metrics, enrichment context (similar past incidents, 
       baseline analysis, host history) בצורה מובנית

3. app/services/agent/tool_adapter.py:
   - המרה בין ה-Tool abstraction שלנו ל-tool schema של Anthropic API
   - def tools_for_anthropic(tools: list[Tool]) -> list[dict]
   - def execute_anthropic_tool_call(tool_use_block, ctx) -> dict
     * validation של input לפי ה-Pydantic model
     * execution דרך ה-tool executor הקיים
     * החזרת result בפורמט שApi מצפה לו
   - טיפול בשגיאות בכל כלי: אם כלי נכשל, ה-agent מקבל error message מובנה 
     (לא exception) כך שיוכל להחליט מה לעשות

4. app/services/agent/investigator.py - הליבה:
   - InvestigatorAgent class
   - async def investigate(incident: Incident) -> InvestigationResult
   - הלולאה:
     ```
     max_iterations = settings.AGENT_MAX_ITERATIONS  # default 8
     max_budget_usd = settings.AGENT_BUDGET_USD  # default 0.50
     
     messages = [initial user message with incident + enrichment]
     checklist = load_checklist(incident.category)
     
     for iteration in range(max_iterations):
         response = await anthropic.messages.create(
             model="claude-sonnet-4-5",  # configurable
             system=system_prompt,
             tools=tools_for_anthropic(available_tools),
             messages=messages,
             max_tokens=4096,
         )
         
         track_cost(response.usage, session_cost)
         if session_cost > max_budget_usd:
             log.warning("budget_exceeded")
             break
         
         if response.stop_reason == "end_turn":
             break
         
         if response.stop_reason == "tool_use":
             tool_results = []
             for block in response.content:
                 if block.type == "tool_use":
                     result = await execute_anthropic_tool_call(block, ctx)
                     tool_results.append({
                         "type": "tool_result",
                         "tool_use_id": block.id,
                         "content": result,
                     })
             messages.append({"role": "assistant", "content": response.content})
             messages.append({"role": "user", "content": tool_results})
             
             # נסה לעדכן את ה-checklist על בסיס התוצאות
             checklist.update_from_tool_result(tool_results)
             
             if checklist.is_complete():
                 # force final synthesis
                 messages.append(final_synthesis_request())
                 continue
     
     # Parse final structured output from last assistant message
     result = parse_investigation_result(messages[-1])
     return result
     ```
   
   - InvestigationResult Pydantic model:
     * hypothesis: str
     * confidence: int (0-100)
     * confidence_rationale: str
     * suggested_action: SuggestedAction (from allowlist)
     * evidence_chain: list[Evidence]
     * alternatives_considered: list[Alternative]
     * tools_executed_summary: list[str]
     * iterations_used: int
     * cost_usd: float
     * duration_seconds: float
     * checklist_completion: dict

5. app/services/agent/actions.py:
   - SuggestedAction schema
   - ActionAllowlist - רשימה סגורה של פעולות אפשריות
   - action_key, description, target_fields (איזה פרמטרים נדרשים), 
     tier (0/1/2/3), requires_approval
   - config/actions.yaml - דוגמה ראשונית:
     * NOTE_IN_TICKET (tier 0)
     * ADD_CORRELATION_COMMENT (tier 0)
     * RESTART_SERVICE (tier 1, אחרי reliability gate)
     * CLEAR_CACHE (tier 1)
     * ACKNOWLEDGE_MAINTENANCE (tier 0)
     * REBOOT_HOST (tier 3, ידני לנצח)
     * ESCALATE_TO_TIER2 (tier 0)
   - ה-agent יכול להציע רק מ-allowlist; validation בקוד

6. app/services/agent/parser.py:
   - parse_investigation_result(assistant_message) -> InvestigationResult
   - מצפה מה-agent שהפלט הסופי יהיה JSON מובנה ב-message האחרון (או XML tags)
   - robust parsing - אם JSON לא תקין, retry עם prompt מתוקן
   - validation עם Pydantic

7. app/services/agent/executor.py:
   - AgentExecutor - public API
   - async def run_for_incident(incident_id: UUID) -> InvestigationResult
   - טיפול ב:
     * lock (למנוע double investigation על אותו incident)
     * persistence של כל step ב-agent_runs table
     * metrics emission (Prometheus: investigations_total, duration, cost)
     * OpenTelemetry trace לכל ה-investigation

8. DB tables חדשות (migration):
   - agent_runs: id, incident_id, started_at, completed_at, iterations, 
     cost_usd, model, status, error
   - agent_run_steps: id, run_id, step_number, role, content, tool_calls, 
     tool_results, duration_ms

9. tests:
   - Mock Anthropic API עם tool_use responses צפויים
   - Loop עוצר אחרי max_iterations
   - Loop עוצר כשה-checklist מלא
   - Cost tracking עובד
   - Tool execution errors לא שוברים את הלולאה
   - Final result parsed correctly עם Pydantic
   - Integration test: incident → investigation → result (end-to-end, mocked LLM)

10. app/core/config.py - תוספות:
    - AGENT_MODEL (default "claude-sonnet-4-5")
    - AGENT_MAX_ITERATIONS (default 8)
    - AGENT_BUDGET_USD (default 0.50)
    - AGENT_MAX_TOKENS (default 4096)
    - ANTHROPIC_API_KEY

דגשים:
- Structured output: השאיפה היא ש-stop_reason="end_turn" יגיע עם JSON מובנה 
  ב-content האחרון. חלופה: tool "submit_investigation" שה-agent חייב לקרוא 
  בסוף - זה למעשה יותר יציב. שקול את שתי הגישות והמלץ.
- כל step ב-DB: חיוני ל-UI (מסך 10) ול-debugging בפרודקשן
- אל תבנה retry פנימי על Anthropic errors - השאר ל-tenacity בשכבה מעליך
- Observability: כל iteration = span ב-OTel עם cost, model, iteration_number

שאלות להבהיר:
- Anthropic API key - יש כבר הגדרה ב-infra או שזה חדש?
- האם אתה רוצה submit_investigation tool לפלט סופי מובנה, או end-turn עם JSON?
- מגבלת עלות יומית גלובלית - יש? (אם כן, אצטרך cost tracker גלובלי)

התחל בסקיצה של ה-loop, אחר כך data models, אחר כך implementation.
```

---

## CHECKLIST

- [ ] Agent loop רץ מ-end-to-end על incident בסיסי
- [ ] Tool use מעביר פרמטרים נכון ומקבל תוצאות
- [ ] Checklist מתעדכן וגורם ל-early exit כשמלא
- [ ] Max iterations וbudget נאכפים
- [ ] InvestigationResult מובנה, validated עם Pydantic
- [ ] Agent run נשמר ב-DB עם כל הצעדים
- [ ] Cost tracking מדויק
- [ ] Alternatives considered נכתבים ב-result (חיוני ל-trust!)
- [ ] Tests עוברים עם mock Anthropic

## פלט צפוי

Investigator שמציע hypotheses מבוססות-evidence עם confidence מכויל. זו הפעם 
הראשונה שמישהו יוכל לומר "המערכת חושבת שהבעיה היא X כי Y" ולא רק "המערכת 
מסכמת מה שהכלים מצאו".

## נקודות חשובות להמשך

- בתקופה הראשונה, **כל hypothesis חייב לעבור אישור אנושי**. זה שלב 06 (Jira) 
  ו-07 (feedback loop). אל תחפוז לאפשר autonomous actions - זה שלב 13.
- שמור את כל ה-prompts ב-version control. שינויי prompts = שינוי התנהגות 
  של המערכת.
- מוטיב חוזר: "evidence-based". אל תיתן ל-agent להפיק hypothesis ללא evidence 
  מוחשית מהכלים.
