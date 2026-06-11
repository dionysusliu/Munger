# Munger Rearchitecture — STATUS / Manifest

Single entry point for resuming work. Last updated 2026-06-10.

## Where things are

**Branch:** `worktree-sp2.2-entity-resolution` (worktree: `.claude/worktrees/sp2.2-entity-resolution`). **PR #3 was merged early at `609a725` (index audit) — `main` LACKS SP3.1 + SP2.2.** This branch carries the SP3.1 + SP2.2 delta off `main`; a fresh PR brings them in.

**Run the backend tests** (the venv pitfall: use the 3.12 venv, NOT system python):
```
cd munger/backend && TEST_DATABASE_URL=postgresql+psycopg://munger_app:Munger.App.2026@localhost:5432/munger_test \
  /Users/chuang/Documents/dev/projects/Munger/munger/backend/.venv/bin/python -m pytest tests/ -q -p no:cacheprovider \
  --ignore=tests/integration/test_provider_gate.py --ignore=tests/integration/test_frontend_smoke.py
```
Current: **115 passed** (the 2 ignored tests need OpenRouter creds / a built frontend).

## Design spec (north-star)

- `docs/superpowers/specs/2026-06-09-munger-data-architecture-design.md` — four-runtime architecture (FastAPI serving · **DBOS** durable spine · Pathway/Ray deferred to scale) over Postgres + LanceDB; least-viable-state data model; rec-sys retrieval funnel; conservative chat + self-improvement; BIG-TABLE test harness; SP0–SP5 roadmap. Includes mermaid diagrams (architecture / read-write paths / background tiers / data model).

## Execution plans (one per sub-project)

| Plan file (`docs/superpowers/plans/`) | Status |
|---|---|
| `2026-06-09-sp0-characterization-infra-test-suite.md` | ✅ DONE — parity suite, 11/11 ingest steps asserted |
| `2026-06-09-sp1-dbos-spine-foundation.md` | ✅ DONE — DBOS spine behind `INGEST_ORCHESTRATOR=dbos` |
| `2026-06-10-sp2.1-graph-edges-foundation.md` | ✅ DONE — `entity_edges` + `EdgeService` (mig 007) |
| `2026-06-10-sp2.3-salience-communities.md` | ✅ DONE — `GraphService` PageRank+Louvain (mig 008) |
| `2026-06-10-sp2.2-entity-resolution.md` | ✅ DONE — `EntityResolutionService`: block(trgm)→score→cluster → soft-merge `canonical_entity_id` + `labeled_pairs` HITL + `unmerge` + `_flatten_chains` (mig 010); `POST /api/entities/{resolve,unmerge,label}` |
| **SP2.3b** (community reports) | ⏳ TODO — LLM summaries + bm25/tfidf topic-labels (txtai-style) per community → GraphRAG global search |
| `2026-06-10-sp3.1-retrieval.md` | ✅ DONE — `RetrievalService`: link + 3-channel (vector/lexical/graph-PPR) + RRF + salience rerank + assemble; `GET /api/search/retrieve` |
| **SP3.2** (vector entity-linking) | ⏳ TODO — `entities.embedding` HNSW (migration) + vector seed-linking + canonical-aware retrieval (COALESCE) |
| **SP4** (chat over retrieval) | ⏳ TODO — conservative read-write chat; smolagents candidate; structural-hole bridging via `showpath`/`betweenness` |

Index audit (no SP): **migration 009** done (FK/hot-path indexes; dropped legacy `entity_graph_edges` matview).

## Project memory (NOT git-tracked — `~/.claude/projects/-Users-chuang-Documents-dev-projects-Munger/memory/`)

- `MEMORY.md` — index
- `munger-data-rearchitecture.md` — full current state, SP progress, txtai takeaways, deferred items, **[[test-run-setup]]**
- `test-run-setup.md` — the venv + test-DB command (above)

## Key code added this session

- DBOS spine: `app/runtime/dbos_app.py` (singleton), `app/runtime/dbos_ingest.py` (workflow + step), `app/runtime/ingest_runner.py` (`orchestrator`/`use_checkpointer` params), `app/worker/runner.py` (`maybe_launch_dbos`)
- Cross-loop fix: `app/core/database.py` — `async_session_maker` is a **ContextVar-routed factory** (do not revert)
- Entity graph: `app/services/edge_service.py` (rebuild_all/update_for_source/top_neighbors), `app/services/graph_service.py` (NetworkX pagerank/communities; interface mirrors txtai's `Graph`, extend with showpath/centrality for SP4 bridging)
- Models: `app/models/entity_edge.py`, `app/models/community.py`; `entities.salience`/`canonical_entity_id`/`community_id`
- Migrations: `alembic/versions/007_*` (entity_edges), `008_*` (communities), `009_*` (index audit)
- Retrieval (SP3.1): `app/services/retrieval_service.py` (link + vector/lexical/graph-PPR + RRF + assemble), `GraphService.personalized_pagerank`, `app/api/retrieval.py` (`GET /api/search/retrieve`), `RuntimeServices.retrieval`
- Resolution (SP2.2): `app/services/entity_resolution_service.py` (block/score/resolve/unmerge/label + `_flatten_chains`), `app/models/labeled_pair.py` (mig 010), `app/api/resolution.py`, `RuntimeServices.entity_resolution`

## Deferred / scale (per the txtai review)

`ingest_events` index trim (model-declared) · **model2vec** static embeddings (bulk-embed throughput) · vector **quantization** int8/binary (LanceDB) · **litellm** (replace hand-rolled multi-provider `LLMService`) · **smolagents** (SP4 chat agent) · Pathway/Ray (SP5).

## Conventions

- New ingest behavior stays behind a flag / additive; default `INGEST_ORCHESTRATOR=graph` unchanged.
- Migrations are **migration-only** (don't add new model-declared indexes — the project applies migrations incrementally on a persisted test DB; from-scratch `001` uses `create_all`).
- Per-SP: write plan → execute (subagent-driven, full review on SQL/logic-heavy tasks) → commit → push → PR per branch. (PR #3 was merged early at index-audit; SP3.1 + SP2.2 land via the next PR off `main`.)
