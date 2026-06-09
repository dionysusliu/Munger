# Deep Interview Spec: Ingest Realtime Progress

## Metadata
- **Profile:** Standard + refinement (rounds 9–12)
- **Rounds:** 12
- **Final ambiguity:** ~10%
- **Threshold:** 20%
- **Context type:** Brownfield
- **Context snapshots:**
  - `.omx/context/ingest-realtime-progress-20260608T162500Z.md`
  - `.omx/context/ingest-realtime-progress-20260608T170000Z.md` (concurrency refinement)
- **Transcript:** `.omx/interviews/ingest-realtime-progress-20260608T163800Z.md`

## Intent (Why)
After uploading large sources (e.g. book PDFs), the Ingest UI feels opaque during long runs. The user wants **visibility into what the agent is doing** — both its reasoning trail and concrete per-step/tool activity — so ingest feels alive and debuggable, not frozen.

## Desired Outcome
1. **Ingest page shows a live chronological timeline** per job while in-flight (and after completion for review): agent messages, tool calls, and tool results — like a mini chat log.
2. **LangGraph ingest remains the canonical pipeline** (DeerFlow-aligned `create_agent` harness).
3. **Legacy WorkflowRun subsystem is removed** to eliminate dual-runtime confusion.
4. **Dedicated worker process** executes ingest jobs in parallel (bounded by infra), decoupled from the API event loop.
5. **Single Postgres database** holds app data, job queue, run events, and LangGraph checkpoints (migrate off SQLite).

## In-Scope
### Backend — LangGraph event capture
- Instrument the LangGraph ingest path (`IngestRunner` / ingest lead agent) to persist run events:
  - Agent messages (AIMessage content)
  - Tool calls (name, args)
  - Tool results (ToolMessage content / errors)
  - Stage/status transitions (existing `Source.status` values)
- Store events in a durable DB table keyed by `source_id` (+ optional `thread_id` / run nonce)
- Extend ingest status API (stable path) to return timeline data for polling:
  - **Preferred:** enrich `GET /api/sources/{id}/status` with `events` (paginated or `since_id` cursor) + `has_more`
  - Alternative child endpoint only if response size forces it: `GET /api/sources/{id}/events` (still under `/sources`)
- Emit events from harness middleware and/or `astream_events` / message hooks during `IngestRunner.run()`
- Polling only for frontend updates (no SSE)

### Backend — Dedicated worker + job queue
- Replace FastAPI `BackgroundTasks` ingest execution with **enqueue-only API**:
  - `POST /api/sources/{id}/ingest` creates a durable job row and returns `202` immediately
  - No LangGraph execution on the API process event loop
- Add **`munger-worker`** service (separate Docker container/process):
  - Polls/claims jobs from Postgres queue (`FOR UPDATE SKIP LOCKED` or equivalent)
  - Runs `IngestRunner` per claimed job
  - Concurrency default: **`max(1, cpu_count - 1)`** per worker process (env override allowed)
- API process stays responsive under N concurrent ingests; worker scales independently
- Jobs survive API restarts; worker picks up `pending`/`running` reconciliation on startup

### Backend — Postgres migration (single DB)
- Migrate all SQLAlchemy models from SQLite (`munger.db`) to **Pigsty Postgres**
- One database (recommended name: `munger`) holds:
  - App tables (sources, wiki, entities, config, …)
  - `ingest_jobs` (or equivalent) queue table
  - `ingest_events` timeline table
  - LangGraph checkpoint tables (via `langgraph-checkpoint-postgres`)
- Remove SQLite as runtime dependency for Munger app data
- Alembic migrations + data migration strategy for any existing local SQLite data (OMX discretion; empty dev DB acceptable)

### Backend — Workflow subsystem removal
- Delete or fully retire:
  - `app/workflow/engine.py` and sequential `{{step:...}}` DSL execution path
  - `POST /api/workflows/{id}/run`, run resume/interrupt endpoints
  - `WorkflowRun`, `WorkflowRunStep` models and related migrations/tables (or provide Alembic downgrade)
  - Workflow-specific tests that only cover the removed engine
- **Preserve** DeerFlow-format SKILL.md loading for LangGraph agents (`default-ingest/SKILL.md` via `app/runtime/harness/skills/`)
- **Preserve** builtin skill files under `data/workflows/` as agent skill definitions (not DSL workflows)

### Frontend — Ingest timeline UI
- Expandable job card shows **live timeline** while polling (2s interval acceptable; OMX may tune)
- Render event types distinctly: agent text, tool call, tool result, status change, error
- Auto-scroll or pin-to-bottom behavior for active jobs (OMX discretion)
- Keep queue list, filters, pagination, upload flow from ingest-job-persistence work
- Full UI/layout autonomy on the Ingest page

## Out-of-Scope / Non-goals
- SSE / WebSocket streaming (polling only for v1)
- Cancel / interrupt ingest from UI
- Wiring Munger analysis or other pipelines to the timeline (ingest only)
- Migrating ingest to WorkflowRun (explicitly rejected)
- Keeping WorkflowRun engine, runs API, DSL parser, or workflow run DB tables
- New top-level nav routes beyond existing Dashboard / Wiki / Ingest
- System Logs page (`Logs.tsx` mock) wiring — unless trivial reuse of same event API
- Human-in-the-loop review gates for ingest
- Exposing raw hidden chain-of-thought beyond what LangChain messages already contain

## Decision Boundaries
**OMX has full implementation autonomy** for:
- Event schema, DB migrations, LangGraph instrumentation approach
- Middleware vs stream-tap design
- Workflow subsystem deletion scope and test updates
- Ingest page timeline UX (layout, polling, styling)
- Internal refactors

**Must preserve:**
- Existing ingest API paths: `POST /api/sources/upload`, `POST /api/sources/{id}/ingest`, `GET /api/sources/{id}/status`, `GET /api/sources`, `DELETE /api/sources/{id}`
- Response backward compatibility: existing status fields (`status`, `error_message`, `recent_logs`) remain; new fields are additive

## Constraints
- Brownfield FastAPI + SQLAlchemy + React/Vite frontend
- **Postgres:** Pigsty Docker at `localhost:5432` (`/Users/chuang/Services/pigsty/docker`); Munger containers connect via `host.docker.internal`
- PDF extraction must not block worker event loop (keep `asyncio.to_thread` for LiteParse)
- Docker dev stack: `munger-backend` (API) + `munger-worker` + existing frontend
- Provider ingest harness must continue to pass after changes
- LLM rate limits may cap effective parallelism below CPU-based concurrency

## Testable Acceptance Criteria
1. `POST /api/sources/{id}/ingest` enqueues a job; API returns before worker finishes
2. Worker process claims and runs multiple ingest jobs in parallel up to concurrency cap
3. API `/api/health` stays responsive while 2+ ingests run on worker
4. `GET /api/sources/{id}/status` returns additive `events` with agent + tool + result entries in chronological order
5. Ingest page expanded card shows timeline updating via polling while job is in-flight
6. Completed jobs retain timeline for post-run review
7. App data reads/writes use Postgres (no SQLite at runtime)
8. `/api/workflows/*/run` and WorkflowRun models are removed or return 410/404; no dead imports
9. LangGraph ingest harness + `default-ingest` skill still completes ingest (entities + wiki)
10. `npm run build` passes; backend tests updated and green for changed areas
11. Existing ingest queue behaviors (pagination, filters, delete, re-ingest) still work

## Architecture Notes (brownfield)

### Current state
```
POST /sources/{id}/ingest
  → BackgroundTasks → IngestRunner
    → LangGraph create_agent (ingest lead)
      → tools: extract_source_text, summarize_source, extract_entities_from_text, create_wiki_pages, finalize_ingest
      → checkpointer thread (messages NOT exposed)
GET /sources/{id}/status → coarse status + last 10 IngestionLog rows
```

### Target state
```
POST /sources/{id}/ingest
  → API inserts ingest_jobs row (pending) in Postgres
  → 202 Accepted immediately

munger-worker (separate process)
  → claim job(s) with SKIP LOCKED, concurrency = cpu_count - 1
  → IngestRunner (instrumented)
    → LangGraph agent + Postgres checkpointer
    → persist ingest_events rows during agent stream
    → update sources.status

GET /sources/{id}/status
  → status + events[] timeline (poll with since_id)
Frontend Ingest card → render timeline
```

### FastAPI event loop — serial or parallel? (resolved)
| Scenario | Behavior today |
|----------|----------------|
| Multiple ingests via separate requests | **Can interleave** on one asyncio loop while awaiting LLM HTTP I/O |
| CPU/sync work on event loop | **Blocks everything** (API + all ingests) — mitigated for PDF via `to_thread` |
| BackgroundTasks | **Not a real queue** — no cap, not durable, runs in API process |
| **Target** | API never runs ingest; worker process owns parallel execution |

### Postgres provisioning (Pigsty)
**OMX may create automatically** using Pigsty DBA credentials (`dbuser_dba` / `DBUser.DBA`):

```sql
-- Run once against Pigsty (as dbuser_dba)
CREATE ROLE munger_app WITH LOGIN PASSWORD '<from env MUNGER_DB_PASSWORD>';
CREATE DATABASE munger OWNER munger_app;
\c munger
CREATE SCHEMA IF NOT EXISTS public;
GRANT ALL ON SCHEMA public TO munger_app;
```

**Connection strings (example):**
- Host Postgres: `postgresql://munger_app:<password>@localhost:5432/munger`
- Munger Docker: `postgresql://munger_app:<password>@host.docker.internal:5432/munger`
- Checkpointer: same DB URL via `MUNGER_CHECKPOINTER_URL` (or derived from `DATABASE_URL`)

**User action required:** Ensure Pigsty is deployed (`make launch` in pigsty/docker). OMX handles role/DB creation via init script or Alembic bootstrap; no manual schema design needed from user beyond providing/accepting env vars in `docker-compose.yml`.

### Suggested event schema (OMX may adjust)
| field | type | notes |
|-------|------|-------|
| id | int | monotonic per source |
| source_id | int | FK |
| event_type | enum | `agent_message`, `tool_call`, `tool_result`, `status_change`, `error` |
| payload | JSON/text | message body, tool name/args, result snippet |
| created_at | datetime | ordering |

## Assumptions Exposed + Resolutions

| Assumption | Resolution |
|------------|------------|
| Ingest runs via WorkflowRun | **False** — LangGraph agent is canonical; WorkflowRun is legacy |
| DeerFlow = WorkflowEngine | **False** — DeerFlow alignment is LangGraph `create_agent` harness + SKILL.md skills |
| Need SSE for "realtime" | **Rejected** — polling sufficient for v1 |
| Must keep workflow runs API | **Rejected** — remove entire subsystem |
| FastAPI event loop serializes all ingests | **Partially true** — interleaves async I/O but shared loop + SQLite limits real parallelism |
| SQLite sufficient for parallel ingest | **Rejected** — migrate to single Postgres DB |
| OMX cannot create Postgres roles/DB | **Rejected** — OMX creates `munger` DB + `munger_app` role via bootstrap |

## Refinement Rounds 9–12 (backend serving)
| Round | Decision |
|-------|----------|
| 9 | Dedicated worker process (DeerFlow-style); API enqueues only |
| 10 | Postgres job queue on existing Pigsty deployment |
| 11 | Concurrency = `cpu_count - 1` per worker (env override OK) |
| 12 | Migrate all app data to Postgres — single DB for app + jobs + checkpoints |

## Pressure-Pass Findings
- **Rounds 4–5:** User initially chose WorkflowRun migration; after architecture explanation, reversed to LangGraph + delete WorkflowRun. Confirms intent is agent observability, not step-DSL run records.
- **Round 9:** User assumed event-loop serial execution; clarified interleaving vs blocking; chose worker separation for true parallel ingest under load.

## Recommended Execution Handoff
1. **`$ralplan`** (recommended) — plan event schema, instrumentation points, workflow deletion migration, frontend timeline
2. **`$ralph`** — persistent implementation until acceptance criteria met
3. **`$autopilot`** — if plan is skipped and direct execution preferred
