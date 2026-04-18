# Stage 04 - IKB (Incident Knowledge Base) + pgvector

## מטרת השלב

לבנות את הזיכרון של המערכת. אחרי השלב, כל incident נשמר עם embedding, יש שליפה
סמנטית של תקלות דומות, יש rolling baselines למטריקות, ויש service שמזין context
לכל investigation.

**זה השלב שהופך את המערכת מ"מגיבה" ל"יודעת".**

## הקשר מוקדם

ראה `CLAUDE.md`.
שלבים 01-03 הושלמו - יש triage שמזין incidents מובנים.

---

## PROMPT (להעברה ל-Claude)

```
אני עובד על פרויקט NOC Agent שמתואר ב-CLAUDE.md. השלבים 01-03 הושלמו (יש 
scaffolding, tool registry, ו-triage pipeline מלא).

בסשן הזה אני בונה את ה-IKB (Incident Knowledge Base) - הזיכרון ארוך-הטווח של 
המערכת. מטרתו: לתת לכל investigation עתידית הקשר היסטורי שיעזור ל-agent להבין 
את התקלה מהר יותר ובדיוק יותר.

דרישות:

1. DB Schema Extensions (Alembic migration):
   - הרחב את טבלת incidents עם:
     * embedding: vector(1536)  -- pgvector column
     * hypothesis: text
     * confidence: smallint  (0-100)
     * suggested_action_key: text
     * resolution_category: text (לרשימה סגורה - ראה להלן)
     * resolution_details: text
     * was_hypothesis_correct: text  ('yes'/'partially'/'no')
     * resolution_time_minutes: integer
     * recurrence_count: integer default 0
     * tags: text[] (flexible labels)
   - טבלה חדשה: metric_baselines
     * id, hostname, metric_name, mean, stddev, p50, p95, p99, 
       sample_count, window_days, computed_at
     * unique constraint על (hostname, metric_name, window_days)
   - טבלה חדשה: resolution_categories (enum table)
     * name, description, category (physical/data_integrity/coupling/general)
     * דוגמאות seed: hardware_replacement, config_change, restart_service, 
       cache_clear, scheduled_maintenance, false_positive, upstream_issue, 
       requires_investigation
   - אינדקסים:
     * HNSW index על embedding (pgvector)
     * btree על (hostname, created_at)
     * btree על (category, resolution_category, created_at)
     * gin על tags

2. app/services/ikb/embeddings.py:
   - EmbeddingService class
   - אפשרויות providers דרך config:
     * "anthropic" - אם יש endpoint embeddings
     * "sentence-transformers" - local model (all-MiniLM-L6-v2, 384 dims, 
       או mpnet-base 768 dims)
     * "openai" - text-embedding-3-small (1536 dims)
   - async def embed(text: str) -> list[float]
   - async def embed_batch(texts: list[str]) -> list[list[float]]
   - caching (Redis) על hash של הטקסט
   - retries + fallback אם provider נופל

3. app/services/ikb/incident_embedder.py:
   - IncidentEmbedder
   - def build_embedding_text(incident: Incident) -> str:
     * מרכיב טקסט מובנה מה-incident: alert name, host, category, metrics summary, 
       hypothesis (אם יש), resolution (אם יש)
     * format קבוע, כך ש-embeddings עקביים
   - async def embed_and_store(incident_id: UUID) -> None
   - async def re_embed_resolved(incident_id: UUID) -> None
     * נקרא אחרי שה-resolution נוסף - מחשב מחדש עם הטקסט העשיר יותר

4. app/services/ikb/similarity.py:
   - SimilarityService
   - async def find_similar_incidents(
         alert_or_incident, 
         limit: int = 5, 
         category_filter: str | None = None,
         min_age_days: int = 1,  -- לא incidents של הדקה האחרונה
         resolved_only: bool = True  -- רק incidents עם resolution
     ) -> list[SimilarIncident]
   - SimilarIncident = incident + similarity_score + relevance_reason
   - משתמש ב-pgvector query: `ORDER BY embedding <=> $1 LIMIT N`
   - מחזיר גם מטדטה: מה היה ה-resolution, כמה זמן לקח, האם ה-hypothesis הקודם 
     היה נכון

5. app/services/ikb/baselines.py:
   - BaselineService
   - async def compute_baselines_for_host(hostname: str, window_days: int = 30) 
     -> list[MetricBaseline]
   - שולף metrics מ-Grafana/TSDB (דרך GrafanaQueryTool), מחשב:
     * mean, stddev
     * p50, p95, p99
     * excludes incidents windows (זמנים שבהם היתה תקלה)
   - שומר ב-metric_baselines עם upsert
   - async def analyze_current_value(hostname, metric, current_value) 
     -> BaselineAnalysis
     * מחזיר: z_score, percentile_rank, is_anomaly, severity_level
   - job שרץ יומית ומרענן את כל ה-baselines (APScheduler או cron)

6. app/services/ikb/enrichment.py:
   - EnrichmentService - זה ה-public entry point
   - async def enrich(incident: Incident) -> EnrichmentContext
   - מחזיר:
     * similar_incidents: list[SimilarIncident] (5 הכי דומים)
     * host_history: dict (total incidents on host, last 30 days count, 
       common resolutions)
     * baseline_analysis: BaselineAnalysis (האם הערך הנוכחי חריג)
     * related_active_incidents: list[UUID] (מה-correlation engine)
     * recurrence_info: dict (האם זה incident חוזר; כמה פעמים; פתרונות קודמים)
   - שמירת ה-enrichment על ה-incident במסד
   - כל השליפות במקביל (asyncio.gather) לחסכון בזמן

7. app/api/incidents.py - endpoints חדשים:
   - GET /incidents/{id}/similar - מחזיר similar incidents
   - GET /incidents/{id}/enrichment - מחזיר את ה-EnrichmentContext המלא
   - GET /hosts/{hostname}/history - historical view על host
   - GET /hosts/{hostname}/baselines - baselines נוכחיים

8. tests:
   - embeddings עובדים, cache פועל
   - similarity search מוצא incidents רלוונטיים (seed data)
   - baselines מחושבים נכון
   - enrichment מחזיר את כל החלקים
   - performance: enrichment של incident חדש < 2 שניות (עם mock Grafana)

9. app/tasks/ - background jobs:
   - daily_baseline_refresh.py
   - weekly_embedding_audit.py (מזהה incidents חדשים ללא embedding)
   - APScheduler integration ב-main.py

דגשים:
- pgvector חייב להיות מותקן ב-DB (extension). הוסף הודעה למשתמש לוודא זאת.
- Embedding provider - שאל את המשתמש איזה הוא רוצה. דיפולט מומלץ: 
  sentence-transformers local (חינם, פרטי, מספיק טוב לinitial).
- Similarity search - חשוב לנרמל embeddings (unit vectors) לdistance יציב.
- Re-embedding אחרי resolution זה **קריטי** - לפני זה, ה-embedding לא כולל את 
  הידע הכי חשוב.

שאלות להבהיר:
- איזה embedding provider?
- יש לך כבר data של incidents קודמים לייבוא? אם כן, אילו שדות?
- האם מטריקות Grafana נגישות בבאtch (לחישוב baselines) או רק per-query?

התחל בmigration + data model, ואז services.
```

---

## CHECKLIST

- [ ] migration רץ, pgvector extension פעיל, אינדקסים נוצרו
- [ ] embeddings מחושבים ונשמרים לכל incident חדש
- [ ] similarity search מחזיר תוצאות רלוונטיות (seed של 10-20 incidents)
- [ ] baselines מחושבים יומית עבור כל host פעיל
- [ ] enrichment service מחזיר את כל החלקים במקביל
- [ ] Re-embedding מופעל אוטומטית אחרי הוספת resolution (זה יקרה בשלב 07)
- [ ] endpoints ל-UI מחזירים נתונים מהר (< 500ms)

## פלט צפוי

כל incident עתידי מגיע ל-investigator עם context עשיר. ה-agent לא מתחיל מאפס -
הוא מתחיל כמו אנג'ינר עם ניסיון של שנים.

## הערה אסטרטגית

זה השלב היקר ביותר ברמת ה-setup (pgvector, embeddings, baselines), אבל **זה גם 
מה שהופך את המערכת לשווה**. בלי IKB, יש לך workflow חמוד שעוד כלי מצטרף אליו. 
עם IKB, יש לך מערכת לומדת.
