# Deep Interview Spec: Munger Backend Pipeline Runtime (v1)

## Metadata
- **Profile:** Standard
- **Rounds:** 8
- **Final ambiguity:** ~13%
- **Threshold:** 20%
- **Context type:** Brownfield
- **Context snapshot:** `.omx/context/backend-pipeline-arch-20260607T000000Z.md`
- **Transcript:** `.omx/interviews/backend-pipeline-arch-20260608T035500Z.md`

## Intent (Why)
Replace Munger's split-brain backend (working `IngestService` vs unwired sequential `WorkflowEngine`) with a **single DeerFlow-inspired LangGraph runtime** that can later host all workflows. Primary drivers:
1. Unified execution path for future workflows
2. Borrow product-tested DeerFlow harness patterns to reduce build time
3. Preserve architecture headroom for **dynamic workflow generation** (future; not v1)

## Desired Outcome
`POST /api/sources/{id}/ingest` executes a **new supervisor + fixed 3-stage LangGraph runtime** (extract text → LLM entity extraction → wiki generation). `IngestService` orchestration is **retired** (thin wrapper acceptable only during cutover). Existing provider harness proves end-to-end success.

## In-Scope (v1)
- New runtime module under `munger/backend/app/runtime/` adapted from DeerFlow harness
- Fixed LangGraph topology:
  - **Supervisor** node (task coordination, stage progression, result aggregation)
  - **3 stages** as tools/middleware (not separate sub-agent LLMs):
    1. Extract text from source
    2. LLM entity extraction (reuse `EntityService`)
    3. Wiki page generation (reuse `WikiService` / `LLMService`)
- Wire `app/api/sources.py` ingest trigger to new runtime
- Copy/adapt DeerFlow modules (worker, checkpointer, factory patterns) into Munger codebase
- Add LangGraph/LangChain dependencies as needed
- Retire `IngestService` orchestration once parity achieved
- Pass existing provider harness: upload → ingest → source-associated entities + wiki

## Out-of-Scope / Non-goals (v1)
- Munger 12-dimension analysis pipeline
- Search, graph API, Munger analysis panel backend
- Dynamic workflow generation at search time (future phase)
- Full workflow catalog / multiple SKILL.md pipelines beyond ingest
- Frontend changes
- SSE/WebSocket streaming (nice-to-have, not required for v1 done)
- Human-in-the-loop interrupt/resume gates (not required for v1 done)
- New comprehensive test suite beyond existing harness (unless needed to make harness pass)

## Decision Boundaries
**OMX has full implementation autonomy**, including:
- Add LangGraph/LangChain dependencies
- Copy/adapt DeerFlow harness files with rename/refactor
- Delete or replace `IngestService` orchestration
- Add/adjust DB schema for run state/checkpoints if needed
- Internal refactors as long as `/sources/{id}/ingest` external contract unchanged
- Keep or freeze legacy sequential `WorkflowEngine` if unused (do not extend for v1)

## Constraints
- Brownfield FastAPI + SQLAlchemy + SQLite stack
- User reports working provider env var (OpenRouter) — prior 403 blocker assumed resolved
- Docker dev stack must remain bootable
- Reuse existing services (`EntityService`, `WikiService`, `LLMService`, `StorageService`) as stage implementations where possible

## Testable Acceptance Criteria
1. `docker compose up` boots backend + frontend successfully
2. `POST /api/sources/upload` + `POST /api/sources/{id}/ingest` completes without error for a test document
3. After ingest, **source-associated** entities exist in DB/API
4. After ingest, **source-associated** wiki pages exist in DB/API
5. Existing harness command passes provider lane:
   - `docker compose run --rm -e BACKEND_BASE_URL=... -e FRONTEND_BASE_URL=... munger-backend python scripts/run_test_harness.py`
6. `IngestService` no longer owns orchestration logic (deleted or thin delegate to runtime)

## Assumptions Exposed + Resolutions

| Assumption | Resolution |
|------------|------------|
| DeerFlow uses hand-built supervisor-subgraph with Researcher/Coder/Reporter | **Partially differs from repo evidence** — DeerFlow uses `create_agent` + middleware + optional task-tool subagents. **v1 adopts user's chosen model:** supervisor + fixed 3-stage graph. |
| Munger `{{step:...}}` DSL must compile to LangGraph now | **Deferred** — v1 uses fixed ingest graph; step-DSL compiler is later phase |
| Must port DeerFlow test harness wholesale | **Resolved:** copy/adapt harness patterns; v1 success = existing Munger provider harness passes |
| OpenRouter key works | **Accepted** per user; verify during execution |

## Pressure-Pass Findings
- **Round 1 revisit (Round 8):** "Borrow DeerFlow code" clarified as **copy/adapt harness modules** into `munger/backend/`, not patterns-only reimplementation.

## Brownfield Evidence

### Munger today
- **Working:** `IngestService.ingest_source()` — `app/services/ingest_service.py`
- **Unwired:** `WorkflowEngine` sequential loop — `app/workflow/engine.py`; no LangGraph in `requirements.txt`
- **Defined but inactive:** `data/workflows/default-ingest/SKILL.md`
- **Ingest trigger:** `app/api/sources.py` → `_run_ingestion_pipeline` calls `IngestService` directly

### DeerFlow borrow targets
| DeerFlow path | Borrow for |
|---------------|------------|
| `packages/harness/deerflow/runtime/runs/worker.py` | Background run execution loop |
| `packages/harness/deerflow/runtime/checkpointer/` | Run persistence |
| `packages/harness/deerflow/agents/factory.py` | Config-driven graph assembly |
| `packages/harness/deerflow/agents/thread_state.py` | Typed state + reducers |
| `packages/harness/deerflow/skills/parser.py` | SKILL.md frontmatter (future) |
| `packages/harness/deerflow/runtime/runs/manager.py` | Run lifecycle registry |

## Proposed v1 Architecture (for planning handoff)

```
POST /sources/{id}/ingest
        │
        ▼
  RunManager.start(ingest_run)
        │
        ▼
  Worker.execute(supervisor_graph)
        │
        ├─ Stage 1: extract_text (StorageService)
        ├─ Stage 2: extract_entities (EntityService + LLMService)
        └─ Stage 3: save_wiki (WikiService + LLMService)
        │
        ▼
  Checkpointer persists run state
        │
        ▼
  Source status = completed; entities + wiki linked to source
```

**Module layout (suggested):**
- `app/runtime/graph/ingest_graph.py` — fixed 3-stage LangGraph compile
- `app/runtime/supervisor.py` — stage orchestration node
- `app/runtime/worker.py` — adapted from DeerFlow worker
- `app/runtime/checkpointer.py` — adapted from DeerFlow
- `app/runtime/state.py` — ingest run state schema
- `app/runtime/tools/` — thin wrappers over existing services

## Residual Risks
- User's DeerFlow mental model (supervisor-subgraph) vs actual DeerFlow `create_agent` implementation — mitigate by copying worker/checkpointer patterns, not blindly copying agent topology
- Provider e2e may still fail if env var not present in Docker compose context
- Global entity/wiki count assertions in harness may be noisy — tighten to source-scoped checks during implementation if harness flakes

## Recommended Execution Handoff
1. **`$ralplan`** (recommended) — architecture validation + implementation plan from this spec
2. **`$autopilot`** — direct execution if plan not needed
3. **`$ralph`** — persistent loop until harness green
4. **`$team`** — if parallel lanes (runtime port + API wiring + harness fix)
