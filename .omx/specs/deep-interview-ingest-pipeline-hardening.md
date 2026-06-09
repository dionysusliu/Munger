# Deep Interview Spec: Ingest Pipeline Hardening

## Metadata

| Field | Value |
|-------|-------|
| Profile | Standard |
| Rounds | 9 (+ follow-up on map retry) |
| Final ambiguity | 13% |
| Threshold | 20% |
| Context type | Brownfield |
| Context snapshot | `.omx/context/ingest-pipeline-hardening-20260609T084735Z.md` |
| Transcript | `.omx/interviews/ingest-pipeline-hardening-20260609T090000Z.md` |
| Prior work | `.omx/specs/deep-interview-cognee-inspired-pipeline-refactor.md`, `.omx/plans/ralplan-cognee-inspired-pipeline-refactor.md` |

## Intent

Harden the landed LangGraph ingest pipeline for **correctness and reliability** before scaling ingest volume. The user rejects any inconsistency between chunks, entities, and relationships — whether from partial writes after crashes, flaky LLM JSON parsing, or duplicate/orphan rows after merge/link steps.

## Desired Outcome

1. **SQL:** Audit every ingest SQL path; collapse unnecessary multi-session patterns (especially `LinkingService` per-match sessions) while keeping per-chunk commits for `Send` map-reduce throughput.
2. **Instructor:** Wire Pydantic + Instructor for extraction/glean structured output; retire hand-rolled `_parse_json` for those paths.
3. **Naming:** Rename `add` → `intake` in Python and observability; adopt `nodes_{phase}.py` file layout (`nodes_intake.py`, `nodes_cognify.py`).
4. **Deferred backlog:** Ship every item deferred from the cognee-inspired refactor ralph pass.

## In-Scope

### Workstream 1 — SQL transaction audit & consolidation

- Audit all SQL/session usage in ingest pipeline:
  - `linking_service.py` (9 session contexts; per-match loop)
  - `map_chunk_service.py` (per-chunk + embed batch)
  - `resolution_service.py` (reference pattern)
  - `chunk_service.py`
  - Graph nodes: `add_nodes.py` → `nodes_intake.py`, `cognify_nodes.py` → `nodes_cognify.py`
  - `ingest_tools.py` (agent fallback)
- **Txn strategy (pragmatic):**
  - Collapse obvious multi-commit loops into single sessions per logical operation (e.g. full `link_entities` pass, full entity merge, embed batch per wave).
  - **Keep** per-chunk atomic commits for `Send` map workers — do not block parallelism with a single cognify-phase txn.
  - Each worker's own writes should still be internally consistent (entities + mentions + offsets in one commit where feasible).
- Document txn boundaries in code comments or `WORKFLOW_ARCH.md` where non-obvious.

#### Map-phase crash robustness & selective retry (decision **b**)

On job requeue after map failure, **remap only failed/missing chunks** — do not full re-chunk and wipe successful workers' data.

**Required behavior:**

| Event | Action |
|-------|--------|
| First map pass | `n_chunk` splits text only if no chunks exist (or content changed); does **not** source-wide `DELETE chunk_extractions` before Send |
| Worker success | Single per-chunk txn: delete extractions for that `chunk_id`, insert glean rounds, update `contextual_prefix` + `embedding`, mark chunk `done` |
| Worker failure (after retries) | No commit for that chunk; mark chunk `failed` with `last_error` |
| Job requeue / resume | Fan-out `Send` only for chunks in `pending` or `failed`; skip `done` chunks |
| Before `n_reduce` | Gate: every `chunk_id` for the source must be `done` (or re-dispatch failures first) |
| Full re-ingest | Explicit operator/API path only: delete chunks + extractions + reset map status when source content changes |

**Implementation sketch (agent decides details):**

- New `chunk_map_status` table (or columns on `chunks`): `map_status` (`pending` \| `running` \| `done` \| `failed`), `map_attempts`, `last_error`, `mapped_at`.
- `map_single_chunk`: idempotent per chunk — `DELETE chunk_extractions WHERE chunk_id = ?` then insert, all in one session/commit.
- `fanout_chunks`: filter to chunks needing work; do not re-send `done` chunks.
- Stale job `reconcile_stale_jobs` → requeue → worker resumes map for failed/pending only; optionally persist `thread_id` on `IngestJob` for LangGraph checkpoint resume of downstream nodes (reduce+), but chunk-level status is the source of truth for map idempotency.
- `n_reduce` raises if any chunk is not `done` — never silently reduce on partial extractions.

**Consistency guarantee:** Successful chunks are never rewritten on retry unless explicitly marked for re-map (e.g. content revision). Reduce/link/wiki only run on a complete map set.

### Workstream 2 — Pydantic + Instructor

- Scope: **extraction and glean only** (`ExtractionResult`, `GleanResult` in `app/schemas/extraction.py`).
- Replace `_parse_json` + manual `model_validate` in `map_chunk_service.py` and `extraction_service.py` with Instructor-enabled structured completion.
- Include retry/validation behavior appropriate for flaky models (agent decides retry count).
- Do **not** migrate unrelated LLM calls (wiki generation, classification) in this pass.

### Workstream 3 — Rename `add` → `intake`

- **Python:**
  - `graphs/add.py` → `graphs/intake.py`
  - `nodes/add_nodes.py` → `nodes/nodes_intake.py`
  - `AddState` → `IntakeState`
  - Parent graph: `graph.add_node("intake", intake_subgraph)` in `ingest.py`
  - `nodes/cognify_nodes.py` → `nodes/nodes_cognify.py` (convention alignment)
- **Observability:**
  - Rename subgraph identifiers and any `GRAPH_STEP_ORDER` / log keys that literally say "add".
  - Keys like `register_source`, `hash_dedup` stay unless they contain "add".
- **Not required:** Breaking REST API contract or renaming unrelated frontend strings that never said "add".

### Workstream 4 — Finish deferred tasks

| Item | Deliverable |
|------|-------------|
| Golden corpus | `tests/fixtures/golden/` + `test_cross_chunk_golden.py` |
| Scripted LLM | `tests/fixtures/fake_llm.py` (`ScriptedLLMService`) |
| Materialized view | `entity_graph_edges` migration (e.g. `005_entity_graph_view.py`) |
| Middleware cleanup | Remove `IngestToolGatingMiddleware` + legacy tool aliases |
| Frontend timeline | `app/src/pages/Ingest.tsx` labels for graph steps |
| Docs | `munger/backend/AGENTS.md`, `WORKFLOW_ARCH.md` truth-up |
| Integration tests | Resume + agent-fallback (`INGEST_ORCHESTRATOR=agent`) paths |
| Map retry | Selective chunk re-map on job requeue; `chunk_map_status` + reduce gate |

## Out-of-Scope / Non-goals

- **No new ingest features:** improve pass, global semantic linking, S3/datalake, lifecycle API.
- Instructor migration beyond extraction/glean.
- Performance optimization as a primary goal (batch size tuning, query plan optimization) unless required for correctness.
- Removing agent fallback path — `INGEST_ORCHESTRATOR=agent` must remain working after middleware cleanup.

## Decision Boundaries

**Full autonomy** on this spec. Agent may decide without user confirmation:

- Exact session refactor patterns and helper abstractions
- Instructor retry counts and error handling
- Golden corpus fixture content and fake LLM scripts
- Materialized view schema and migration numbering
- Middleware removal approach and alias deprecation strategy
- `GRAPH_STEP_ORDER` key renames where they contain "add"

**Escalate only if:** change would break production ingest or require irreversible API breakage.

## Constraints

- Brownfield; Postgres-only; graph orchestration default (`INGEST_ORCHESTRATOR=graph`).
- `Send` map-reduce parallelism must not be sacrificed for strict per-phase atomicity.
- `pytest tests/ -v` with `TEST_DATABASE_URL` → `munger_test`.
- Frontend verify: `npm run build` + `npm run lint` when `Ingest.tsx` changes.
- Migration `004` assumed applied; new migrations sequential.

## Testable Acceptance Criteria

1. **SQL:** No ingest service opens a new `async_session_maker()` inside a tight loop (e.g. per text-mention match). Linking + merge operations use ≤1 session per logical pass.
2. **SQL:** `map_single_chunk` uses one commit per chunk: extractions + `contextual_prefix` + `embedding` together.
3. **Map retry:** After simulated worker failure, requeue remaps only failed chunks; `done` chunks' extractions unchanged.
4. **Map gate:** `n_reduce` refuses to run (or graph routes to re-dispatch) when any chunk is not `done`.
5. **Instructor:** `instructor` imported and used for extraction/glean; `_parse_json` not used on those paths.
6. **Instructor:** Invalid LLM JSON triggers Instructor retry or structured error — not silent entity drop.
7. **Rename:** No `add.py`, `add_nodes.py`, or `AddState` in `app/runtime/graphs/`; files follow `nodes_{phase}.py`.
8. **Rename:** Graph parent node and observability keys use `intake` not `add`.
9. **Deferred:** Golden corpus test exists and passes; `fake_llm.py` used in at least one test.
10. **Deferred:** `entity_graph_edges` materialized view migration exists; refresh documented.
11. **Deferred:** `IngestToolGatingMiddleware` removed; agent path still passes integration test.
12. **Deferred:** `Ingest.tsx` shows correct labels for all `GRAPH_STEP_ORDER` steps.
13. **Regression:** `pytest tests/unit/ -v` green; new integration tests pass against `munger_test`.

## Assumptions Exposed & Resolutions

| Assumption | Resolution |
|------------|------------|
| Per-phase atomic txn is required | **Rejected** after pressure pass — pragmatic minimum preferred |
| All LLM calls need Instructor | **Rejected** — extraction/glean only |
| Rename touches REST API | **Rejected** — Python + observability only |
| Deferred items optional | **Rejected** — all mandatory this pass |
| Agent path can be removed | **Not stated** — keep agent fallback working |
| Job requeue = full re-chunk + remap | **Rejected** — selective remap of failed/missing chunks only (decision **b**) |
| Source-wide extraction delete at map start | **Rejected** — per-chunk delete on write; full wipe only on explicit re-ingest |

## Pressure-Pass Findings

**Round 7:** User initially chose per-phase atomicity (round 3) but under Send parallelism pressure chose **pragmatic consolidation** — fix egregious multi-session patterns without all-or-nothing cognify rollback.

**Follow-up (map retry):** User chose **(b) selective chunk re-map** on job requeue — preserve successful workers' data; track per-chunk map status; gate reduce on completeness.

## Brownfield Evidence

- `linking_service.py`: ~9 `async_session_maker()` contexts; text-mention loop opens session per match.
- `map_chunk_service.py`: per-chunk session + separate embed batch.
- `resolution_service.py`: single session (good reference).
- `instructor>=1.0.0` in requirements; unused in app code.
- Current naming: `graphs/add.py`, `nodes/add_nodes.py`, `AddState`.
- 29 unit tests pass; golden corpus, fake_llm, materialized view, middleware removal, UI labels, integration tests not shipped.

## Technical Touchpoints

```
munger/backend/app/services/{linking_service,map_chunk_service,resolution_service,chunk_service,extraction_service,llm_service}.py
munger/backend/app/runtime/graphs/{ingest,intake,cognify,state}.py
munger/backend/app/runtime/graphs/nodes/{nodes_intake,nodes_cognify,chunk_map}.py
munger/backend/app/schemas/extraction.py
munger/backend/app/runtime/pipeline_events.py
munger/backend/tests/fixtures/{golden,fake_llm.py}
munger/backend/tests/{unit,integration}/
munger/backend/alembic/versions/005_*.py  # chunk_map_status + entity_graph_edges may share or split migrations
munger/backend/app/models/chunk.py  # map_status columns if not separate table
app/src/pages/Ingest.tsx
munger/backend/AGENTS.md, WORKFLOW_ARCH.md
```

## Suggested Execution Order

1. Migration: `chunk_map_status` (columns on `chunks` or dedicated table)
2. Map retry + per-chunk atomic `map_single_chunk` + reduce gate + fanout filter
3. Rename (intake + nodes layout) — reduces churn in later diffs
4. SQL txn audit + consolidation (linking, resolution patterns)
5. Instructor wiring for extraction/glean
6. Deferred backlog (tests → materialized view → middleware → UI → docs)
7. Full pytest + frontend verify
