# PRD: Munger Backend Pipeline Runtime v1

**Slug:** backend-pipeline-arch  
**Source spec:** `.omx/specs/deep-interview-backend-pipeline-arch.md`  
**Status:** Approved v4 (consensus reached)

---

## Requirements Summary

Replace Munger's ad-hoc `IngestService` orchestration with a **LangGraph-based ingest runtime** executing: **extract text → summarize → LLM entity extraction → wiki generation → index update**. Wire `POST /api/sources/{id}/ingest` to the new runtime; retire `IngestService` orchestration. v1 done = provider harness passes.

**Substrate investment (explicit):** LangGraph `StateGraph` seeds future unified runtime. v1 is lean: no checkpointer, no `WorkflowRun` records, no DeerFlow worker/manager port.

**Spec deviation (signed off):** Deep-interview named a distinct "supervisor node." v1 uses a **linear 5-node graph** where stage progression = edges and `finalize` aggregates completion. Distinct supervisor node deferred to dynamic-workflow phase (branching/coordination).

---

## RALPLAN-DR Summary

### Principles
1. **Reuse services, rewrite orchestrator** — wrap existing services; orchestrator rewrite is deliberate substrate investment
2. **Minimal LangGraph** — `StateGraph` + `graph.ainvoke()` in `BackgroundTasks`; no checkpointer, no DeerFlow worker port
3. **Single execution path** — ingest API → `IngestRunner` only
4. **Harness is the gate** — preserve non-fatal semantics; `Source.status` is run record
5. **Freeze legacy `WorkflowEngine`** — no v1 extension

### Decision Drivers
1. Time-to-working pipeline (minimal infra)
2. Future unified runtime (graph factory + typed state seam)
3. Parity + delete `IngestService` orchestration

### Options

| Option | Verdict |
|--------|---------|
| **A — LangGraph linear graph + `ainvoke`, no checkpointer, `Source.status` only** | **Chosen** |
| B — Full DeerFlow worker/manager port | Rejected (YAGNI, SSE coupling) |
| C — Plain Python runner, no LangGraph | Rejected (user decision) |

---

## IngestRunState (inter-node contract)

```python
class IngestRunState(TypedDict, total=False):
    source_id: int
    text: str
    summary: str
    entities: list[dict]       # serialized entity refs from extract_entities node
    wiki_page_ids: list[int]
    error: str | None          # set only on fatal extract failure
    status: str                # mirrors Source.status for observability
```

Nodes read/write subsets. Fatal path: `extract_text` sets `error` → graph routes to `mark_failed` → END.

---

## Acceptance Criteria

1. `docker compose up -d` boots stack; `/api/health` 200
2. Upload + ingest → `Source.status == completed`
3. **Source-associated entities:** after ingest, find entity via `GET /api/entities?search=Atlas` (or similar seeded name), then `GET /api/entities/{id}/mentions` includes `source_id` matching ingested source
4. **Source-associated wiki:** `GET /api/wiki?search={title}` returns ≥1 page (existing harness pattern)
5. Deterministic pytest suite passes with no regressions; new unit tests in `tests/unit/test_ingest_graph.py` added (baseline + new tests all green)
6. Provider harness passes with `OPENROUTER_API_KEY`
7. `IngestService.ingest_source` deleted (not shim); callers use `IngestRunner` directly
8. Munger 12-dim not invoked; `MungerService` removed from `sources.py` and `IngestService.__init__`
9. Summary/entities/wiki/index failures → still `completed` (only empty text → `failed`)

---

## Implementation Steps

### Step 0 — Baseline
Record pytest deterministic count + harness result.

### Step 1 — Dependencies + scaffold
**Files:** `requirements.txt`, `app/runtime/`

```
langgraph>=1.1
langchain-core>=0.3
```

```
app/runtime/
  __init__.py
  state.py           # IngestRunState
  context.py         # RuntimeServices(settings, storage, llm, entity, wiki)
  ingest_runner.py   # build graph, ainvoke, no WorkflowRun
  nodes/
    extract_text.py
    summarize.py
    extract_entities.py
    save_wiki.py
    finalize.py
    mark_failed.py
  graph/
    ingest_graph.py
```

**Run record:** `Source.status` + `error_message` only. No `WorkflowRun` in v1 (avoids `workflow_id` FK on fresh DB).

### Step 2 — Stage nodes

**DB rule:** each node opens/commits/closes own `async_session_maker()` session (`ingest_service.py:139,168,196` pattern).

**Fatality:**

| Node | Error behavior | Source.status |
|------|----------------|---------------|
| extract_text | Fatal if no text | `extracting` → `failed` or continue |
| summarize | Skip if no LLM; warn on error | `summarizing` |
| extract_entities | Skip if no LLM; warn on error | `extracting_entities` |
| save_wiki | Warn on error | `creating_pages` |
| finalize | Index + log; always sets terminal | `completed` |
| mark_failed | Terminal | `failed` |

Port from `ingest_service.py:59-128,177-285,368-379`.

**LLM=None:** mirror existing silent skip (`:83,94,192`), not spurious warnings.

**Re-ingest safety:** `/ingest` resets status to `pending` (`sources.py:374`); nodes should tolerate re-run.

### Step 3 — Graph compile
**File:** `app/runtime/graph/ingest_graph.py`

```
START → extract_text → [fail? mark_failed : summarize] → extract_entities → save_wiki → finalize → END
```

```python
graph.compile()  # NO checkpointer for v1
await compiled.ainvoke(initial_state)  # no thread_id required
```

`build_ingest_graph(services) -> CompiledGraph` — factory seam for future variants.

### Step 4 — API wiring
**File:** `app/api/sources.py:62-84`

```python
runner = IngestRunner(get_settings())
await runner.run(source_id)
```

Remove `MungerService` import (`:25`) and construction (`:75`).

### Step 5 — Delete IngestService orchestration
**File:** `app/services/ingest_service.py`

- Delete `ingest_source` and stage helpers moved to `app/runtime/nodes/`
- Remove `MungerService` from `__init__` (`:51-53`)
- Delete `ingest_service.py`; update `app/services/__init__.py` (remove `IngestService` export)

### Step 6 — Tests

**New:** `tests/unit/test_ingest_graph.py` — compiles; mocked nodes; fatal vs non-fatal routing

**Update:** `tests/integration/test_provider_gate.py` — add source-scoped entity check:
```python
entities = httpx.get(f"{BASE}/api/entities", params={"search": "Atlas Dynamics"}).json()
entity_id = entities["items"][0]["id"]
mentions = httpx.get(f"{BASE}/api/entities/{entity_id}/mentions").json()
assert any(m["source_id"] == source_id for m in mentions["mentions"])
```
Keep global delta assertions as secondary signal.

### Step 7 — Verify
```bash
docker compose run --rm munger-backend pytest -q
docker compose run --rm -e BACKEND_BASE_URL=... -e FRONTEND_BASE_URL=... \
  munger-backend python scripts/run_test_harness.py
```

---

## Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| Non-fatal regression | Fatality table + AC #9 |
| DB session across nodes | Per-node session rule |
| WorkflowRun FK on fresh DB | Dropped WorkflowRun for v1 |
| Checkpointer thread_id crash | No checkpointer v1 |
| Entity association unproven | Mentions API assertion Step 6 |
| langgraph pin mismatch | Pin after compile test in Step 1 |

---

## ADR

**Decision:** LangGraph linear 5-node graph, `graph.compile()` without checkpointer, `IngestRunner.ainvoke` in BackgroundTasks, `Source.status` as sole run record.

**Drivers:** User LangGraph intent; minimal infra (driver #1); harness gate.

**Alternatives:** DeerFlow worker port (rejected); plain runner (rejected); WorkflowRun records (rejected — FK trap on fresh DB).

**Supervisor deviation:** Spec's supervisor responsibilities absorbed by linear edges + `finalize` until dynamic branching needed.

**Consequences:** No resume/HITL/streaming v1. Phase 2 adds supervisor node, checkpointer, `WorkflowRun` with lifespan workflow seeding.

**Follow-ups:** Phase 2 supervisor + SQLite checkpointer; Phase 3 SKILL.md compiler; Phase 4 `source_id` on entities list API.

---

## Out of Scope (v1)
- Munger 12-dim, WorkflowRun, checkpointer, DeerFlow worker/manager, SSE, HITL, dynamic workflows, frontend

---

## Changelog
- **v2→v3:** Dropped WorkflowRun + MemorySaver; enumerated IngestRunState; source-scoped entity via mentions API; explicit supervisor spec deviation; delete (not shim) IngestService; fixed log helper ref `:368+`
- **v3→v4 (Critic):** AC #5 allows new unit tests; `services/__init__.py` cleanup; entity search pinned to "Atlas Dynamics"

---

## Follow-up Staffing Guidance

### `$ralph` (recommended)
| Lane | Agent | Reasoning | Task |
|------|-------|-----------|------|
| 1 | executor | medium | Steps 1-3: runtime scaffold + graph |
| 2 | executor | medium | Steps 4-5: API wire + delete IngestService |
| 3 | test-engineer | medium | Step 6: unit + harness assertion |
| 4 | verifier | medium | Step 7: full harness green |

### `$team` (optional parallel)
| Worker | Task |
|--------|------|
| W1 | `app/runtime/` graph + nodes |
| W2 | `sources.py` wiring + IngestService deletion |
| W3 | tests + harness hardening |

**Team verification:** W1-W3 complete → run full pytest + provider harness → hand to verifier.

**Launch hints:**
```
$ralph .omx/plans/prd-backend-pipeline-runtime-v1.md
$team .omx/plans/prd-backend-pipeline-runtime-v1.md
```
