# Munger Rearchitecture — STATUS / Manifest

Single entry point for resuming work. Last updated 2026-06-10.

## Where things are

**Branch:** `claude/amazing-faraday-8ea246` (worktree: `.claude/worktrees/amazing-faraday-8ea246`). Open as **PR #3** → https://github.com/dionysusliu/Munger/pull/3 (30 commits ahead of `main`).

**Run the backend tests** (the venv pitfall: use the 3.12 venv, NOT system python):
```
cd munger/backend && TEST_DATABASE_URL=postgresql+psycopg://munger_app:Munger.App.2026@localhost:5432/munger_test \
  /Users/chuang/Documents/dev/projects/Munger/munger/backend/.venv/bin/python -m pytest tests/ -q -p no:cacheprovider \
  --ignore=tests/integration/test_provider_gate.py --ignore=tests/integration/test_frontend_smoke.py
```
Current: **93 passed** (the 2 ignored tests need OpenRouter creds / a built frontend).

## Design spec (north-star)

- `docs/superpowers/specs/2026-06-09-munger-data-architecture-design.md` — four-runtime architecture (FastAPI serving · **DBOS** durable spine · Pathway/Ray deferred to scale) over Postgres + LanceDB; least-viable-state data model; rec-sys retrieval funnel; conservative chat + self-improvement; BIG-TABLE test harness; SP0–SP5 roadmap. Includes mermaid diagrams (architecture / read-write paths / background tiers / data model).

## Execution plans (one per sub-project)

| Plan file (`docs/superpowers/plans/`) | Status |
|---|---|
| `2026-06-09-sp0-characterization-infra-test-suite.md` | ✅ DONE — parity suite, 11/11 ingest steps asserted |
| `2026-06-09-sp1-dbos-spine-foundation.md` | ✅ DONE — DBOS spine behind `INGEST_ORCHESTRATOR=dbos` |
| `2026-06-10-sp2.1-graph-edges-foundation.md` | ✅ DONE — `entity_edges` + `EdgeService` (mig 007) |
| `2026-06-10-sp2.3-salience-communities.md` | ✅ DONE — `GraphService` PageRank+Louvain (mig 008) |
| **SP2.2** (entity resolution) | ⏳ TODO — write plan: block(pgvector ANN)→score→cluster → fill `entities.canonical_entity_id` + new `labeled_pairs`; reversible/HITL |
| **SP2.3b** (community reports) | ⏳ TODO — LLM summaries + bm25/tfidf topic-labels (txtai-style) per community → GraphRAG global search |
| **SP3** (retrieval) | ⏳ TODO — multi-channel recall (PPR over `entity_edges` + vector + BM25) → rerank (salience/recency) → entity-centric assembly. salience+edges+communities all ready |

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

## Deferred / scale (per the txtai review)

`ingest_events` index trim (model-declared) · **model2vec** static embeddings (bulk-embed throughput) · vector **quantization** int8/binary (LanceDB) · **litellm** (replace hand-rolled multi-provider `LLMService`) · **smolagents** (SP4 chat agent) · Pathway/Ray (SP5).

## Conventions

- New ingest behavior stays behind a flag / additive; default `INGEST_ORCHESTRATOR=graph` unchanged.
- Migrations are **migration-only** (don't add new model-declared indexes — the project applies migrations incrementally on a persisted test DB; from-scratch `001` uses `create_all`).
- Per-SP: write plan → execute (subagent-driven, full review on SQL/logic-heavy tasks) → commit → push to PR #3.
