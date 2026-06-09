# RALPLAN: Ingest Pipeline Hardening

**Slug:** `ingest-pipeline-hardening`  
**Spec:** `.omx/specs/deep-interview-ingest-pipeline-hardening.md`  
**Context:** `.omx/context/ingest-pipeline-hardening-20260609T084735Z.md`  
**Prior shipped:** `.omx/plans/ralplan-cognee-inspired-pipeline-refactor.md` (v2.2)  
**Type:** Brownfield hardening — map retry, txn consolidation, Instructor, rename, mandatory backlog  
**Mode:** Consensus (RALPLAN-DR + ADR) — Planner → Architect → Critic  
**Date:** 2026-06-09  
**Status:** **APPROVED v1.0** — Architect `REQUEST_CHANGES` addressed; Critic gaps closed in this revision

---

## Executive summary

The LangGraph ingest pipeline (add + cognify, Send map-reduce, LinkingService) is functionally landed but not production-hardened. This plan delivers:

1. **Per-chunk map status + selective re-map** on job requeue (decision **b**)
2. **Single atomic commit** per chunk (extractions + prefix + embedding)
3. **`n_map_gate`** graph loop — never reduce on partial map
4. **LinkingService** txn consolidation (no per-match sessions)
5. **Instructor** for extraction/glean structured output
6. **Rename** `add` → `intake`, `nodes_{phase}.py` layout
7. **Mandatory backlog** from cognee refactor (golden tests, MV, middleware removal, UI, docs)

**Not in scope:** new ingest features (improve pass, semantic linking, S3, lifecycle API).

---

## Brownfield ground truth (verified)

| Fact | Evidence |
|------|----------|
| `map_single_chunk` = 3 sessions | `map_chunk_service.py:183-259` — extract commit then embed commit |
| Source-wide extraction wipe before Send | `cognify_nodes.py:46-51` |
| `fanout_chunks` sends all chunk_ids | `cognify_nodes.py:63-73` — no status filter |
| Send failure aborts graph | `chunk_map.py:58` — exception propagates |
| `n_reduce` has no completeness gate | `cognify_nodes.py:99-112` |
| Fresh `thread_id` every run | `ingest_runner.py:134-138` — no resume |
| `reconcile_stale_jobs` clears `thread_id` | `ingest_job_service.py:126` |
| `sources.content_hash` exists | `models/source.py:19` |
| `IngestJob.thread_id` nullable | `models/ingest_job.py:32` |
| Linking per-match sessions | `linking_service.py:167-179` |
| `instructor` in requirements, unused | no app imports |
| `GRAPH_STEP_ORDER` = 11 steps | `pipeline_events.py:32-44` |
| `Ingest.tsx` shows 8 steps | `Ingest.tsx:81-90` — missing register, hash_dedup, link_entities |
| Migration head | `004_cross_chunk_linking` |
| Unit tests | 29 pass; no golden corpus, no map-retry integration |

---

## 1. RALPLAN-DR

### Principles

1. **Chunk is the atomic unit of map consistency** — one commit bundles extraction + prefix + embedding; `map_status` tracks lifecycle.
2. **Never silently reduce on partial map** — `n_map_gate` blocks `n_reduce`; reduce only when all chunks `done`.
3. **Idempotent retry without rewriting success** — requeue remaps `pending`/`failed` only; `done` chunks untouched.
4. **Pragmatic txn consolidation elsewhere** — linking/merge ≤1 write session per pass; zero sessions inside loops.
5. **Brownfield-safe** — additive migration; agent fallback preserved; no new product features.

### Decision drivers (top 3)

1. **Correctness** — user rejects inconsistency between chunks, entities, relationships.
2. **Crash robustness** — map worker failures recoverable without full re-chunk / redo successful LLM work.
3. **Operational completeness** — ship deferred tests, docs, UI, middleware cleanup from prior refactor.

### Viable options

#### Map retry on requeue

| Option | Verdict |
|--------|---------|
| **(a) Full re-chunk + remap** | **REJECTED** — user rejected; wastes successful worker output |
| **(b) Selective chunk re-map via `map_status`** | **CHOSEN** |
| **(c) Staging tables + promote** | **REJECTED** — excess complexity; (b) + per-chunk atomic commit sufficient |

#### Graph incomplete-map handling

| Option | Verdict |
|--------|---------|
| Raise inside `n_reduce` | **REJECTED** — reduce may run on partial data if gate misplaced |
| **`n_map_gate` node + conditional re-`Send`** | **CHOSEN** |
| Infinite re-Send without wave cap | **REJECTED** — bounded by `ingest_map_max_waves` (default 3) |

#### Resume / thread_id

| Option | Verdict |
|--------|---------|
| **Option A: fresh `thread_id` on job requeue; chunk status drives map idempotency** | **CHOSEN** |
| Option B: reuse `IngestJob.thread_id` + checkpoint resume across requeues | **REJECTED** — Send + checkpoint resume underspecified; contradicts stale reconcile |

#### map_status storage

| Option | Verdict |
|--------|---------|
| Columns on `chunks` | **CHOSEN** |
| Separate table | Rejected — 1:1 with chunks |

### Pre-mortem (deliberate mode)

| Scenario | Mitigation |
|----------|------------|
| Two workers race same chunk | CAS `UPDATE chunks SET map_status='running' WHERE id=? AND map_status IN ('pending','failed') RETURNING id` |
| Send child throws | `process_chunk` try/except; mark `failed` in DB; return error metric; wave converges |
| Reduce runs 9/10 | `n_map_gate` queries DB; re-Send or fail after wave cap |
| Legacy half-done chunks backfilled as `done` | Backfill requires `chunk_extractions` (glean_round=0) **AND** `embedding IS NOT NULL` |
| Infinite gate loop | `map_retry_wave` in state; max `ingest_map_max_waves` (default 3); then `MapIncompleteError` → job failed |
| Stale `running` after worker crash | `n_map_gate` reclaims `running` where `updated_at < now() - ingest_map_stale_minutes` (default 15) → `failed` |
| Instructor latency regression | `ingest_instructor_enabled` setting (default true); tests use fake LLM |
| Rename breaks imports | Dedicated phase after map/linking stable; compile smoke first |

---

## 2. PRD

### Problem

Ingest can leave inconsistent state: split per-chunk commits (extraction without embedding), source-wide extraction wipe on every map pass, no selective retry after partial map failure, hand-rolled JSON parsing, ambiguous `add` naming, and 7 deferred deliverables from the prior refactor.

### Users

Operators ingesting sources at scale; developers extending the pipeline.

### Success metrics

- Zero silent partial reduce
- Requeue after 1-of-N chunk failure remaps only failed chunk(s)
- All 13 acceptance criteria in spec pass
- `pytest tests/ -v` green; `npm run build && npm run lint` when UI touched

---

## 3. Architecture

### 3.1 Cognify graph topology (Send mode)

```
START → n_chunk
      → fanout_chunks (DB: pending|failed only)
      → Send("n_process_chunk") × N
      → [Send convergence]
      → n_map_gate
      → conditional:
           • list[Send] → n_process_chunk  (incomplete; wave < max)
           • "n_reduce"                    (all done)
      → n_reduce → n_link → n_summarize → n_wiki → n_finalize → END
```

**`cognify.py` change:** replace `graph.add_edge("n_process_chunk", "n_reduce")` with edge to `n_map_gate` + conditional edges.

### 3.2 Per-chunk map lifecycle

```
pending | failed
    → CAS running (map_attempts++)
    → LLM extract + glean + embed (outside txn)
    → single txn:
        DELETE chunk_extractions WHERE chunk_id
        INSERT glean rounds
        UPDATE contextual_prefix, embedding
        map_status=done, clear map_last_error, mapped_at=now()
    → on error: short txn → map_status=failed, map_last_error
```

**`done` invariant:** extractions (glean_round=0) exist AND `embedding IS NOT NULL` (unless `ingest_allow_null_embedding=true` for dev).

### 3.3 `n_chunk` behavior

| Condition | Action |
|-----------|--------|
| No chunks for source | `split_chunks` |
| `source.content_hash` changed since last chunk row | `split_chunks` (resets all `map_status=pending`) |
| Chunks exist, hash unchanged | Skip split; use existing chunk IDs |
| Never | Source-wide `DELETE chunk_extractions` |

### 3.4 Job requeue (Option A)

- `reconcile_stale_jobs` → `pending` (unchanged)
- New `IngestRunner.run` → fresh `thread_id` (`ingest-{source_id}-{nonce}`)
- Map idempotency from `chunks.map_status`, not checkpoint
- Within single `ainvoke`, `map_retry_wave` state supports gate re-Send loops

### 3.5 Service mode (`INGEST_MAP_MODE=service`)

`n_map` (batch `map_chunks`) must honor same `map_status` lifecycle and call gate-equivalent completeness check before reduce. Refactor `map_chunks` to iterate pending/failed chunks or delegate to `map_single_chunk`.

---

## 4. Implementation phases

### Phase 0 — Migration `005_chunk_map_status`

**File:** `alembic/versions/005_chunk_map_status.py`

```sql
ALTER TABLE chunks ADD COLUMN map_status VARCHAR(20) NOT NULL DEFAULT 'pending';
ALTER TABLE chunks ADD COLUMN map_attempts INT NOT NULL DEFAULT 0;
ALTER TABLE chunks ADD COLUMN map_last_error TEXT;
ALTER TABLE chunks ADD COLUMN mapped_at TIMESTAMPTZ;
CREATE INDEX ix_chunks_source_map_status ON chunks (source_id, map_status);
```

**Backfill:**
```sql
UPDATE chunks c SET map_status = 'done', mapped_at = NOW()
WHERE EXISTS (
  SELECT 1 FROM chunk_extractions ce
  WHERE ce.chunk_id = c.id AND ce.glean_round = 0
) AND c.embedding IS NOT NULL;

-- else remains 'pending'
```

**Config additions** (`config.py`):
- `ingest_map_max_waves: int = 3`
- `ingest_map_stale_minutes: int = 15`
- `ingest_instructor_enabled: bool = True`
- `ingest_allow_null_embedding: bool = False`

### Phase 1 — Map hardening + `n_map_gate`

| File | Changes |
|------|---------|
| `models/chunk.py` | map_status columns |
| `map_chunk_service.py` | CAS, single txn, status updates |
| `cognify_nodes.py` | `n_chunk` no source delete; `n_map_gate`; reclaim stale `running` |
| `chunk_map.py` | `process_chunk` try/except |
| `cognify.py` | wire `n_map_gate` conditional edges |
| `state.py` | `map_retry_wave: int` on `CognifyState` |
| `chunk_service.py` | `split_chunks` optional guard; expose `needs_resplit(source_id)` |

**Post-wave-3 behavior:** `n_map_gate` raises `MapIncompleteError` with chunk IDs still not `done` → `ingest_runner` catches → `fail_source` + job `failed`. Chunks remain `failed` for operator visibility.

### Phase 2 — Instructor (extraction/glean)

| File | Changes |
|------|---------|
| `llm_service.py` | `chat_structured(messages, response_model)` via instructor |
| `map_chunk_service.py` | replace `_parse_json` in extract/glean |
| `extraction_service.py` | same |

Retries: 3 on validation error; log and mark chunk `failed` if exhausted.

### Phase 3 — LinkingService txn consolidation

| File | Changes |
|------|---------|
| `linking_service.py` | batch text-mention inserts; single write session for co-mention links |

Target: zero `async_session_maker()` inside loops; ≤2 sessions for full `link_source`.

### Phase 4 — Rename `add` → `intake`

| From | To |
|------|-----|
| `graphs/add.py` | `graphs/intake.py` |
| `nodes/add_nodes.py` | `nodes/nodes_intake.py` |
| `nodes/cognify_nodes.py` | `nodes/nodes_cognify.py` |
| `AddState` | `IntakeState` |
| Parent node `"add"` | `"intake"` |

Update imports, `test_ingest_graph.py`, `ingest.py` routing.

### Phase 5 — Mandatory backlog

| Deliverable | Path |
|-------------|------|
| Scripted LLM | `tests/fixtures/fake_llm.py` |
| Golden corpus | `tests/fixtures/golden/` |
| Golden test | `tests/unit/test_cross_chunk_golden.py` |
| Materialized view | `006_entity_graph_edges.py` + refresh doc |
| Middleware removal | delete `IngestToolGatingMiddleware`; simplify agent path |
| Frontend timeline | `app/src/pages/Ingest.tsx` — 11 steps |
| Integration tests | map failure + selective requeue; agent fallback |
| Docs | `munger/backend/AGENTS.md`, `WORKFLOW_ARCH.md` |

---

## 5. Test specification

### Phase 1 (blocking)

| ID | Type | Assertion |
|----|------|-----------|
| T0 | migration | Backfill: extraction without embedding → `pending` |
| T1 | unit | `map_single_chunk` one commit session for writes |
| T1b | unit | `process_chunk` exception → returns error metric; chunk `failed` in DB |
| T2 | integration | 3 chunks, fail #2 → #1,#3 `done`; requeue → only #2 remapped |
| T2b | integration | Requeue unchanged `content_hash` → no `split_chunks` |
| T3 | integration | Incomplete map → `n_reduce` not called |
| T3b | integration | `n_map_gate` re-Sends only `pending`/`failed` |
| T3c | integration | `map_retry_wave` = max → `MapIncompleteError`; job failed |
| T3d | unit | Stale `running` past TTL → reclaimed `failed`; re-dispatched |
| T4 | unit | `fanout_chunks` DB filter skips `done` |
| T4b | integration | Requeue uses new `thread_id`; selective remap via status |

### Phase 2–5

| ID | Type | Assertion |
|----|------|-----------|
| T5 | unit | Instructor retries invalid JSON |
| T6 | unit | `link_source` no session in loop |
| T7 | unit | Graph compiles; no `add.py` / `AddState` |
| T8 | golden | Cross-chunk merge+link under fake LLM |
| T9 | integration | Agent path completes without gating middleware |
| T10 | frontend | `npm run build` + `npm run lint` |
| T11 | unit/service | `INGEST_MAP_MODE=service` honors map_status gate |

### Verification commands

```bash
# Backend
cd munger/backend
export TEST_DATABASE_URL=postgresql+psycopg://munger_app:PASSWORD@localhost:5432/munger_test
alembic upgrade head
pytest tests/ -v

# Frontend (if Ingest.tsx changed)
cd app && npm run build && npm run lint
```

---

## 6. ADR-005: Selective chunk re-map with `n_map_gate`

| Field | Content |
|-------|---------|
| **Decision** | Per-chunk `map_status` on `chunks`; selective re-map on requeue; `n_map_gate` conditional re-Send before reduce |
| **Drivers** | Correctness; crash recovery without redoing successful LLM work; user decision (b) |
| **Alternatives** | (a) full re-chunk — rejected; (c) staging tables — rejected; raise in `n_reduce` — rejected; checkpoint resume across requeues — rejected |
| **Why chosen** | Preserves successful chunk work; bounded in-graph retry; DB is source of truth; aligns with Send parallelism |
| **Consequences** | Migration 005; graph topology change; CAS + TTL reclaim logic; service mode must align |
| **Follow-ups** | Operator "force full re-ingest" API; metrics on `map_attempts`; embedding-null dev flag |

---

## 7. Acceptance criteria (from spec)

1. No session in tight loop in linking
2. `map_single_chunk` single commit per chunk
3. Requeue remaps only failed chunks
4. `n_map_gate` blocks reduce until all `done`
5. Instructor for extraction/glean
6. Instructor retry on bad JSON
7. `nodes_{phase}.py` layout; no `add.py`
8. Observability uses `intake`
9. Golden corpus + fake_llm tests pass
10. `entity_graph_edges` MV exists
11. Middleware removed; agent path works
12. `Ingest.tsx` 11 steps
13. Full pytest green

---

## 8. Execution handoff

### Recommended: `$ralph`

Sequential phases 0→5; verification after each phase; persistence until AC 1–13 pass.

```
$ralph .omx/plans/ralplan-ingest-pipeline-hardening.md
```

### Alternative: `$team` (parallel lanes after Phase 1)

| Lane | Owner | Scope | Reasoning |
|------|-------|-------|-----------|
| A | executor | Phase 2 Instructor | medium — LLM integration |
| B | executor | Phase 3 linking txn | medium — SQL refactor |
| C | executor | Phase 4 rename | low — mechanical |
| D | test-engineer | Phase 5 tests + golden | high — test design |
| E | executor | Phase 5 UI + docs | low |

**Merge order:** Phase 1 trunk first → A+B parallel → C → D+E → verifier.

### Team verification path

1. `test-engineer`: T0–T4b integration against `munger_test`
2. `verifier`: AC checklist 1–13
3. `code-reviewer`: linking session audit + gate topology

### Suggested reasoning by lane

- Map/gate (Phase 1): **high** — concurrency + graph edges
- Instructor: **medium**
- Rename/docs: **low**

---

## 9. Consensus record

| Round | Architect | Critic |
|-------|-----------|--------|
| 1 | REQUEST_CHANGES — gate topology, thread_id, backfill | ITERATE — T3b-d, wave cap, draft contradictions |
| 2 | (addressed in v1.0) | **APPROVE** (this revision) |

**Artifacts:**
- Draft: `.omx/plans/ralplan-ingest-pipeline-hardening-draft.md`
- Approved: `.omx/plans/ralplan-ingest-pipeline-hardening.md`
