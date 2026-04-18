# Stage 02 - Tool Registry + Migration of Existing Tools

## מטרת השלב

לבנות את ה-Tool Registry - האבסטרקציה שדרכה כל כלי אבחון (קיים או חדש) משתלב במערכת.
אחרי השלב, הכלים הקיימים שלך (Grafana queries, SSH checks, DB queries, pcap parsers)
עטופים ב-abstraction אחיד, עם schema ברור, timeouts, safety levels, ו-registry דינמי
שה-workflow engine וה-agent יכולים לשלוף ממנו.

## הקשר מוקדם

ראה `CLAUDE.md` בשורש הפרויקט.
שלב 01 (Foundation) הושלם - יש scaffolding עובד של backend.

---

## PROMPT (להעברה ל-Claude)

```
אני עובד על פרויקט NOC Agent שמתואר ב-CLAUDE.md. השלב הקודם (01_foundation) 
הושלם - יש לי scaffolding של FastAPI, DB, webhook endpoint.

בסשן הזה אני בונה את Tool Registry - האבסטרקציה שדרכה כל כלי אבחון של המערכת
עובד. יש לי כבר קוד קיים של כלים שצריך לשלב (Grafana queries, SSH checks, 
PCAP analysis, netflow DB queries וכו').

דרישות עבור ה-Tool abstraction:

1. app/tools/base.py:
   - Protocol/ABC שמגדיר Tool:
     * name (ClassVar[str])
     * description (ClassVar[str]) - תיאור ש-LLM ישתמש בו לבחירת הכלי
     * categories (ClassVar[list[str]]) - אילו קטגוריות incident מתאימות
     * input_model (ClassVar[type[BaseModel]])
     * output_model (ClassVar[type[BaseModel]])
     * timeout_seconds (ClassVar[int] = 30)
     * safety_level (ClassVar[Literal["read_only", "side_effects"]] = "read_only")
     * async def execute(self, input: BaseModel, ctx: ToolContext) -> BaseModel
   - ToolContext dataclass עם: incident_id, correlation_id, logger, http_client, 
     db_session, config
   - ToolExecution Pydantic model שמתעד הרצה: tool_name, input, output, 
     duration_ms, status, error, started_at, completed_at

2. app/tools/registry.py:
   - ToolRegistry class עם:
     * register(tool_class) - רישום כלי חדש
     * get(name) -> Tool
     * list_for_category(category) -> list[Tool]
     * list_all_schemas_for_llm() -> list[dict] (JSON schemas לAnthropic tool use)
   - Decorator @register_tool שרושם אוטומטית
   - Singleton instance שנטען ב-FastAPI startup

3. app/tools/executor.py:
   - execute_tool(tool_name, input, ctx) -> ToolExecution
   - מטפל ב:
     * timeout (asyncio.timeout)
     * שגיאות (ToolExecutionError עם פרטים)
     * לוגינג structured לפני/אחרי
     * מדידת duration
     * שמירת ה-ToolExecution ל-DB
     * emit event ל-Redis pubsub (ל-WebSocket UI)

4. דוגמאות מיגרציה - בנה 3 wrappers לדוגמה:
   a. GrafanaQueryTool - שאילתה ל-Grafana datasource
      input: datasource_id, query (PromQL/SQL), time_range
      output: DataFrame-like (timestamps + values), meta
   
   b. SSHCheckProcessesTool - בדיקת תהליכים על שרת
      input: hostname, top_n (default 5), sort_by ("cpu" | "mem")
      output: list of {pid, name, cpu_pct, mem_pct, user}
   
   c. CheckDataFreshnessTool - בדיקת hermetciity של טבלה
      input: table_name, timestamp_column, threshold_minutes
      output: last_record_ts, minutes_since_last, is_fresh (bool), gap_ranges

   **חשוב**: שים מימוש placeholder (`raise NotImplementedError` עם הסבר) ל-execute,
   כך שאוכל להחליק את הקוד הקיים שלי לתוך זה מאוחר יותר. אבל כן מלא schemas, 
   metadata, registration.

5. tests/test_tool_registry.py:
   - רישום של mock tool
   - הרצה דרך executor עם timeout שמצליח
   - הרצה עם timeout שנכשל
   - בדיקת list_for_category
   - בדיקת schemas ל-LLM

6. תיעוד ב-app/tools/README.md:
   - איך רושמים כלי חדש (דוגמת קוד)
   - איך אני עוטף קוד קיים (checklist)
   - דוגמה מלאה של הגירה מפונקציה רגילה ל-Tool

דרישות איכות - כרגיל לפי CLAUDE.md.

שאלות הבהרה לפני שאתה מתחיל:
- האם אתה רוצה לראות את הקוד הקיים שלי (למשל pcap_session_checker.py) כדי 
  להתאים את ה-abstraction? אם כן, אני אשתף.
- האם ToolContext צריך להכיל משהו נוסף שספציפי לארגון שלי (credentials vault, 
  feature flags)?

התחל בעץ תיקיות והצגה קצרה של התכנון, ואז קבצים.
```

---

## CHECKLIST

- [ ] `app/tools/base.py` מוגדר עם Protocol + ToolContext + ToolExecution
- [ ] `app/tools/registry.py` עובד: register/get/list/schemas
- [ ] `app/tools/executor.py` מטפל ב-timeout, errors, logging, persistence
- [ ] 3 דוגמאות Tool classes רשומות (אף אם הלוגיקה placeholder)
- [ ] tests עוברים
- [ ] README עם הוראות הגירה ברורות
- [ ] Registry נטען ב-FastAPI startup

## מטלות אחרי הסשן

1. עטוף את הכלים הקיימים שלך - כלי אחר כלי
2. כתוב tests לכל כלי אחרי העטיפה
3. ודא שה-schemas שגויים נתפסים (Pydantic validation) בזמן רישום

## פלט צפוי

אחרי השלב, יש לך:
- Tool abstraction אחיד ונקי
- Registry דינמי שה-agent יוכל לשלוף ממנו
- Path ברור להגירת כל הקוד הקיים
- יסוד שה-workflow engine (שלב הבא) נבנה עליו
