> **ARCHIVED** — Historical snapshot. For current architecture read [ARCHITECTURE.md](./ARCHITECTURE.md) and [AGENTS.md](./AGENTS.md). Do not implement from this file.

# Current Progress

## Completed

- Switched local Docker runtime to OpenRouter env wiring in `munger/docker-compose.yml`.
- Fixed local deployment issues so the stack boots successfully:
  - frontend Docker build now uses the real React app from `app/`
  - backend image no longer depends on unnecessary system toolchain install
  - SQLite Docker path fixed to `sqlite:////app/data/munger.db`
- Added deterministic backend test harness in `munger/backend/tests/`:
  - `test_system_api.py`
  - `test_sources_api.py`
  - `test_wiki_entities_search_api.py`
  - `test_workflows_api.py`
  - shared fixtures in `tests/conftest.py`
- Added integration lane in `munger/backend/tests/integration/`:
  - `test_provider_gate.py`
  - `test_frontend_smoke.py`
- Added harness entrypoint: `munger/backend/scripts/run_test_harness.py`
- **LangGraph ingest runtime v1** (ralplan + ralph):
  - New `munger/backend/app/runtime/` — linear 5-node graph (extract → summarize → entities → wiki → finalize)
  - `POST /api/sources/{id}/ingest` wired to `IngestRunner`; `IngestService` deleted
  - Added `langgraph>=1.1`, `langchain-core>=0.3` dependencies
  - Unit tests: `tests/unit/test_ingest_graph.py` (4 tests)
  - Provider e2e: source-scoped entity assertion via mentions API

## Backend Fixes Landed

- `munger/backend/app/api/sources.py`
  - duplicate uploads checked before writing files
  - storage paths uniquified to avoid collisions
  - ingest now runs via LangGraph `IngestRunner` in background
- `munger/backend/app/api/config.py`
  - fixed provider-route `httpx` import issue
- `munger/backend/app/api/entities.py`
  - fixed mentions query/response bug
- `munger/backend/app/api/workflows.py`
  - fixed workflow run listing order bug
- `munger/backend/app/workflow/builtins.py`
  - built-in workflows now load correctly under Docker bind mounts
- `munger/backend/Dockerfile`
  - preserves built-in workflows outside `/app/data`

## Verification Evidence

- Deterministic backend suite:
  - `docker compose run --rm munger-backend pytest -q`
  - result: `13 passed, 3 deselected` (was 9; +4 unit tests)
- Integration suite:
  - `docker compose run --rm -e BACKEND_BASE_URL=http://host.docker.internal:18000 -e FRONTEND_BASE_URL=http://host.docker.internal:13000 munger-backend pytest -q -m integration`
  - result: `1 passed, 2 skipped` (provider e2e skipped on OpenRouter 403 ToS)
- Combined harness:
  - `docker compose run --rm -e BACKEND_BASE_URL=... -e FRONTEND_BASE_URL=... -e OPENROUTER_API_KEY=... munger-backend python scripts/run_test_harness.py`
  - result: deterministic lane passes; integration lane `BLOCKED EXTERNAL DEPENDENCY` (OpenRouter 403 ToS)
- Live stack:
  - backend healthy on `http://localhost:18000/api/health`
  - frontend returns `200` on `http://localhost:13000`
- Architect verification: **APPROVE** (ingest runtime matches approved PRD v4)

## Current Blocker

- Provider-backed integration lane blocked by external OpenRouter behavior:
  - `/api/config/test-model` returns `403` Terms-of-Service failure
  - harness correctly reports `blocked external dependency`
  - Runtime code ready; provider e2e cannot prove LLM path until OpenRouter account/key works

## Residual Risks

- Provider e2e still uses global entity/wiki count deltas as secondary signal (mentions API now primary for entities).
- Frontend smoke is intentionally thin.
- `WorkflowEngine` sequential path frozen but not removed.
- Phase 2 follow-ups: supervisor node, checkpointer, SKILL.md compiler.

## Next Steps

1. Resolve OpenRouter ToS/403 and rerun provider harness to prove full ingest→entity→wiki e2e.
2. Phase 2: add supervisor node + SQLite checkpointer for resume/HITL.
3. Phase 3: SKILL.md → LangGraph compiler; wire `default-ingest` workflow.
