# Ralplan: Ingest Realtime Progress + Worker + Postgres Migration

**Source:** `.omx/specs/deep-interview-ingest-realtime-progress.md`  
**Context:** `.omx/context/ingest-realtime-progress-20260608T170000Z.md`  
**Mode:** Consensus (RALPLAN-DR deliberate)  
**Status:** APPROVED v3 — Architect CONCERNS addressed; Critic APPROVE (manual pass after subagent stall)

---

## RALPLAN-DR Summary

### Principles
1. **API enqueues, worker executes** — FastAPI never runs LangGraph ingest on its event loop.
2. **Single Postgres truth** — app data, job queue, ingest events, and LangGraph checkpoints share one `munger` database on Pigsty.
3. **Additive API contracts** — existing `/sources/*` paths and status fields remain; new fields (`job_id`, `events`) are additive only.
4. **Observable ingest by default** — agent messages, tool calls, and tool results persisted for polling UI (per-step, not token stream).
5. **One runtime path** — delete WorkflowRun/DSL engine; LangGraph + SKILL.md skills remain canonical.

### Decision Drivers
1. BackgroundTasks on a single uvicorn loop cannot provide durable, bounded parallel ingest under load.
2. User requires agent thinking trail + per-step visibility.
3. Pigsty Postgres deployed; migration unlocks queue + checkpoints + concurrency.

### Viable Options

| Option | Pros | Cons | Verdict |
|--------|------|------|---------|
| **A. Phased with atomic queue+worker slice** | Enqueue+worker ship together (no dark window); DB migration gated; each slice verifiable | More steps than big-bang | ✅ **Chosen (v2)** |
| B. Big-bang single PR | One integration gate | Unbisectable; high regression risk | ❌ Rejected |
| C. Events+UI first on SQLite, worker later | Fast user value | Contradicts user's Postgres+worker decision in rounds 9–12 | ❌ Rejected for v1 scope |
| D. In-process asyncio pool only | Smallest diff | No durability/checkpoint/parallel goals | ❌ Rejected |

---

## Pre-mortem

| Scenario | Mitigation |
|----------|------------|
| Postgres bootstrap fails | One-shot init job; clear startup logs; health gate on DB |
| Stale `running` jobs after crash | Independent per-job heartbeat task; reconciliation TTL > worst-case PDF OCR |
| Concurrent checkpoint writes fail | Pool-backed `AsyncPostgresSaver` or per-job checkpointer |
| Phase 1 without worker = dark ingest | **Merge Phase 1+2 atomically** — never remove BackgroundTasks until worker ships |
| Event payload bloat | `since_id` cursor; 4KB cap on tool result payloads |
| Workflow deletion breaks skills | Keep all `data/workflows/**/SKILL.md` + Dockerfile `/app/builtin-workflows` copy |

---

## ADR

**Decision:** Phased delivery with **atomic queue+worker**, Postgres on psycopg (not asyncpg), pool-backed checkpointer, event timeline, workflow deletion.

**Drivers:** Durable parallel ingest, observability, Pigsty Postgres, API responsiveness.

**Alternatives considered:** asyncpg driver; enqueue-only before worker; WorkflowRun path; SSE — rejected.

**Why chosen:** Fixes Architect blockers; preserves additive API; uses existing `psycopg` in requirements.

**Consequences:** `munger-worker` container; SQLite retired; `sqlite-vec` removed (unused); Alembic replaces `create_all` for prod.

**Follow-ups:** Multi-worker scale-out; cancel/interrupt; token streaming if `_astream` added later.

---

## Implementation Phases

### Phase 0 — Postgres bootstrap & DB layer
**Files:** `docker-compose.yml`, `config.py`, `database.py`, `alembic/env.py`, `scripts/bootstrap_postgres.py`, `requirements.txt`

1. **URLs (psycopg, not asyncpg):**
   - `DATABASE_URL=postgresql+psycopg://munger_app:${MUNGER_DB_PASSWORD}@host.docker.internal:5432/munger`
   - `MUNGER_CHECKPOINTER_URL=postgresql://munger_app:${MUNGER_DB_PASSWORD}@host.docker.internal:5432/munger` (strip `+psycopg` for libpq DSN)
2. **One-shot init container** `munger-db-init` (not API startup):
   - Connect as `dbuser_dba` to Pigsty
   - `CREATE ROLE munger_app` / `CREATE DATABASE munger` if missing
   - DBA creds not in long-running API/worker env
3. **`database.py`:**
   - Support `postgresql+psycopg://`
   - Gate `set_sqlite_pragma` by dialect (keep for test SQLite)
4. **Alembic fix:**
   - `env.py`: use **sync** URL (`postgresql+psycopg://` works with sync engine)
   - Import **all** models including workflow tables (initial migration captures current schema)
   - Author initial migration explicitly
   - **Gate `init_db()`/`create_all`** in `main.py` when `DATABASE_URL` is Postgres (Alembic owns schema)
5. **Requirements:** remove `sqlite-vec` (unused); keep `aiosqlite` for test SQLite
6. **Timestamps:** use timezone-aware `timestamptz` + `datetime.now(UTC)` for new tables

**Data migration:** existing local `munger.db` data is **not** migrated — empty Postgres dev DB is acceptable (per spec).

**Test strategy:** `tests/conftest.py` keeps SQLite for unit tests; add `tests/integration/test_postgres_worker.py` marked optional/skip-if-no-`TEST_DATABASE_URL` for queue+parallel ingest.

**Acceptance:** API boots on Postgres; tables via Alembic; unit tests pass on SQLite; integration test proves 2 parallel jobs when `TEST_DATABASE_URL` set.

---

### Phase 1+2 — Job queue + worker (ATOMIC — no dark window)
**Files:** new `app/models/ingest_job.py`, `app/worker/`, `sources.py`, `docker-compose.yml`, `runtime/harness/checkpointer.py`

**Never merge enqueue-only API without worker in same PR.**

#### Schema `ingest_jobs`
| column | notes |
|--------|-------|
| id, source_id, status | `pending`→`claimed`→`running`→`completed`/`failed` |
| thread_id, error_message, claimed_by | |
| heartbeat_at | updated by **independent asyncio task** per job |
| created_at, updated_at | timestamptz |

**Partial unique index (required):** one active job per source  
`UNIQUE (source_id) WHERE status IN ('pending','claimed','running')`

#### API (`sources.py`)
- `POST /{id}/ingest`: insert job (`pending`), set source `pending`, return **202**:
  ```json
  { "message": "Ingestion triggered", "source_id": 1, "job_id": 42 }
  ```
  (keeps existing `message` — additive `job_id`)
- Active job exists → return 202 with same `job_id` (idempotent)
- **Remove** `BackgroundTasks.add_task` in same commit as worker

#### Checkpointer (blocker fix)
- Replace singleton single-connection saver with **`AsyncConnectionPool`**-backed saver OR per-job checkpointer instance
- Integration test: 2 parallel `IngestRunner.run()` succeed without "operation in progress"

#### Worker (`python -m app.worker`)
- Claim: `SELECT ... FOR UPDATE SKIP LOCKED` up to `MUNGER_WORKER_CONCURRENCY` (default `max(1, cpu_count-1)`)
- Per-job: spawn heartbeat task (interval 30s) independent of agent stream
- Reconciliation on startup: requeue `running`/`claimed` with `heartbeat_at` > 10 min stale
- Docker: same image as backend, `command: python -m app.worker`, **`extra_hosts: host.docker.internal`**, same LLM/DB env

**Acceptance:** AC #1–3 — enqueue immediate, 2 parallel ingests, API health responsive.

---

### Phase 3 — Ingest event instrumentation
**Files:** `ingest_runner.py`, new `app/runtime/events.py`, `app/models/ingest_event.py`, `sources.py` status handler

#### Schema `ingest_events`
`id`, `source_id`, `job_id`, `event_type`, `payload` (JSONB), `created_at`

#### Instrumentation
- `IngestRunner.run`: use `agent.astream_events(version="v2")` (or message iteration on result)
- **Per-step only** — `MungerLLMChatModel` has `_agenerate` only, no `_astream`; timeline shows complete messages per agent step (matches polling UX)
- Persist: `agent_message`, `tool_call`, `tool_result`, `status_change`, `error`
- Truncate tool result payloads to 4KB in DB

#### API (`GET /sources/{id}/status`)
- Additive fields: `events[]`, `events_has_more`, accept `?since_id=&limit=50`
- Keep `recent_logs` for backward compat

**Acceptance:** AC #4 — ordered events for test ingest; `since_id` returns deltas only.

---

### Phase 4 — Workflow subsystem removal
**Files:** delete `app/workflow/engine.py`, run endpoints in `workflows.py`, `WorkflowRun` models; update `models/__init__.py`, `api/router.py`

**Keep:**
- All `data/workflows/**/SKILL.md` (harness loader reads these)
- Dockerfile copy to `/app/builtin-workflows`
- `app/runtime/harness/skills/` loader

**Delete:**
- `WorkflowEngine`, `WorkflowParser` DSL execution, run/resume/interrupt APIs
- `WorkflowRun`, `WorkflowRunStep` tables (follow-up Alembic migration after ingest green)
- Workflow-only tests

**Acceptance:** AC #8 — no `WorkflowEngine` in runtime path; ingest + skills still work.

---

### Phase 5 — Frontend ingest timeline
**Files:** `app/src/lib/api.ts`, `app/src/pages/Ingest.tsx`

- Extend types: `events`, `events_has_more`, `job_id`
- Poll status with `since_id` cursor; append new events
- Timeline in expanded card: distinct styles per `event_type`
- Auto-scroll bottom for in-flight expanded jobs
- Preserve queue pagination/filters/delete

**Acceptance:** AC #5, #6, #10, #11 — build passes; live + retained timeline.

---

## Verification matrix

| AC | Verification |
|----|--------------|
| 1 | POST ingest → 202 + job row before completion |
| 2 | 2 ingests parallel in worker logs |
| 3 | `/api/health` <1s during 2 ingests |
| 4 | `/status?since_id=0` ordered events |
| 5–6 | Browser timeline live + post-complete |
| 7 | Postgres sources rows; no runtime SQLite |
| 8 | `/workflows/1/run` → 404 |
| 9 | `docker compose run munger-backend python scripts/run_test_harness.py` with Postgres env |
| 10 | `npm run build`; `pytest tests/ -v` |
| 11 | Queue filters/pagination/delete |

**Harness env update:** `docker-compose.yml` sets `DATABASE_URL` + `MUNGER_CHECKPOINTER_URL`; document Pigsty must be running before `docker compose up`.

### Test layers
- **Unit:** job claim, event serializer, unique index, checkpointer pool
- **Integration:** 2 parallel ingests + checkpoint writes; enqueue idempotency
- **E2E:** upload → timeline in UI
- **Observability:** heartbeat + reconciliation logs

---

## Execution staffing

### `$ralph` order (sequential)
0. Phase 0 (Postgres + Alembic) — **gate**
1. Phase 1+2 (queue + worker + checkpointer pool) — **atomic**
2. Phase 3 (events + status API)
3. Phase 5 (frontend)
4. Phase 4 (workflow deletion)

### `$team` lanes
| Lane | Scope |
|------|-------|
| A | Phase 0: Postgres, Alembic, docker init |
| B | Phase 1+2: worker, jobs, checkpointer pool |
| C | Phase 3: events instrumentation |
| D | Phase 5: frontend timeline |
| E | Phase 4: workflow deletion (after B+C green) |

**Team verification:** B+C integration (2 parallel ingests + events) before D merges. E last.

**Launch:** `$team .omx/plans/ralplan-ingest-realtime-progress.md`

---

## Critic verdict (v3)

**APPROVE** — Plan satisfies deliberate-mode gates after v2 revisions.

| Criterion | Status |
|-----------|--------|
| Principle-option consistency | ✅ Atomic P1+P2 honors "always-green ingest"; additive `job_id` |
| Alternatives fairly explored | ✅ Rejected options have explicit rationale |
| Risk mitigation | ✅ Pre-mortem + heartbeat pool Alembic fixes |
| Testable AC | ✅ 11 AC mapped to verification matrix |
| Architect blockers | ✅ psycopg, checkpointer pool, Alembic, SKILL.md scope |

Minor improvements merged in v3: test strategy, harness env, no SQLite data migration.

---

## Changelog
- v1 DRAFT: Initial plan
- v2: Architect CONCERNS — psycopg, checkpointer pool, atomic P1+P2, Alembic, heartbeat, unique index, additive API, SKILL.md scope
- v3: Critic APPROVE — test strategy, harness env, data migration note
