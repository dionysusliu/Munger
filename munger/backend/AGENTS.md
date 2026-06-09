<!-- Parent: ../../AGENTS.md -->

# Backend Agent Guide (`munger/backend/`)

Read [`../../ARCHITECTURE.md`](../../ARCHITECTURE.md) and [`WORKFLOW_ARCH.md`](./WORKFLOW_ARCH.md). Stack ops: [`../AGENTS.md`](../AGENTS.md).

## Layer map

```
app/api/        → HTTP routes (sources, wiki, entities, search, munger, config)
app/schemas/    → Pydantic models
app/services/   → Business logic (llm, wiki, entity, storage, search, ingest jobs)
app/models/     → SQLAlchemy ORM
app/core/       → config, database (Postgres only)
app/runtime/    → LangGraph ingest agent harness
app/worker/     → Job poll loop
alembic/        → Migrations (current head: 006_entity_graph_edges)
```

**Removed (do not reference):** `app/workflow/`, `app/models/workflow.py`, `/api/workflows`, SQLite paths.

## Ingest path

```
POST /api/sources/{id}/ingest
  → ingest_jobs (pending)
  → munger-worker claims job
  → IngestRunner.run(source_id, job_id)
       → graph (default): intake + cognify LangGraph subgraphs
       → agent (fallback): LangChain agent, all ingest tools exposed
  → ingest_events[] for UI timeline
  → source.status = completed | failed
```

## Active skill (runtime)

| Skill | File | Status |
|-------|------|--------|
| `ingest` | `data/workflows/default-ingest/SKILL.md` | **Active** — used by worker |

Loader: `app/runtime/harness/skills/loader.py`  
Agent: `app/runtime/agents/ingest_lead_agent.py`

## Dormant skills (not executed)

| File | Status |
|------|--------|
| `data/workflows/munger-12-dimension/SKILL.md` | Legacy `{{step:…}}` format — not wired |
| `data/workflows/quick-summary/SKILL.md` | Legacy — not wired |
| `data/workflows/entity-extract-only/SKILL.md` | Legacy — not wired |

12-dimension analysis runs via `POST /api/munger/analyze/{source_id}` (`munger_service.py`), not these SKILL files.

## Ingest graph (default)

Subgraphs: `intake` (register → parse → hash_dedup) and `cognify` (chunk → map → gate → reduce → link → wiki).

Per-chunk `map_status` on `chunks` enables selective re-map on retry. See `app/services/chunk_map_status.py`.

## Ingest tools (agent fallback)

Defined in `app/runtime/tools/ingest_tools.py` — no progressive gating middleware.

## Database

- **Production/dev DB:** `munger` on Pigsty Postgres
- **Tests:** `munger_test` only — `TEST_DATABASE_URL` required; conftest aborts if DB name is `munger`
- Bootstrap: `scripts/bootstrap_test_postgres.py`
- Migrations run on API startup (`app/main.py` lifespan)

## Tests

```bash
cd munger/backend
export TEST_DATABASE_URL=postgresql+psycopg://munger_app:PASSWORD@localhost:5432/munger_test
python scripts/bootstrap_test_postgres.py   # first-time
pytest tests/ -v
```

Session fixture: `alembic upgrade head` once; per-test `TRUNCATE` (not `drop_all`).

## LLM / OpenRouter

Ingest uses `app/services/llm_service.py`. Docker defaults (`docker-compose.yml`):

- `LLM_DEFAULT_PROVIDER=openrouter`
- `LLM_DEFAULT_MODEL=deepseek/deepseek-v4-flash` (chat)
- `LLM_EMBEDDING_MODEL=qwen/qwen3-embedding-8b` (embeddings)
- `LLM_EMBEDDING_DIMENSIONS=768` (pgvector column width; MRL truncate)

OpenRouter requires **provider-qualified** model ids for both chat and embed (e.g. `qwen/...`, not `nomic-embed-text`). Set `OPENROUTER_API_KEY` in `munger/.env`.

## LangSmith (ingest observability)

Full ingest graph tracing per [LangSmith project routing](https://docs.langchain.com/langsmith/log-traces-to-project) and [LangGraph tracing](https://docs.langchain.com/langsmith/trace-with-langgraph):

- **Static project:** `LANGSMITH_PROJECT=munger-ingest` (also sets `LANGCHAIN_PROJECT`)
- **Enable:** `LANGSMITH_TRACING=true`, `LANGSMITH_API_KEY=...`
- **Worker flush:** `LANGCHAIN_CALLBACKS_BACKGROUND=false` so traces export before job exit

Bootstrap: `app/observability/langsmith_setup.py` (worker + API startup).

What gets traced:

- Root run: `ingest-source-{id}` (LangGraph parent graph via `LangChainTracer` callbacks)
- LangGraph nodes: native spans with `langgraph_node` metadata (`n_register` … `n_finalize`, `n_process_chunk`)
- Custom LLM httpx calls: `LLMService.chat` / `embed_texts` via `@traceable`

**Viewing the tree in LangSmith**

1. Open project `munger-ingest` → click root run **`ingest-source-{id}`** (not individual `llm_chat` rows).
2. Toggle **Waterfall** (top-right) for the nested span tree: `intake` → `cognify` → inner `LangGraph` → nodes → `llm_chat`.
3. **Graph** diagram: open the inner **`LangGraph`** run under **`cognify`** for the cognify pipeline graph (`n_chunk` → `n_process_chunk` → …). The root graph only shows `intake` → `cognify`.
4. In-progress runs may show an empty Graph tab until the root run completes; Waterfall still shows partial children.

## Local dev (without Docker)

```bash
export DATABASE_URL=postgresql+psycopg://munger_app:PASSWORD@localhost:5432/munger
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Key API prefixes

`/api/sources`, `/api/wiki`, `/api/entities`, `/api/search`, `/api/munger`, `/api/config`, `/api/health`
