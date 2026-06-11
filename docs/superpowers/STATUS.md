# Munger Rearchitecture — STATUS / Manifest

Single entry point for resuming work. Last updated 2026-06-10.

## Where things are

**Branch:** `worktree-frontend-chat` (worktree: `.claude/worktrees/frontend-chat`), off `main`. `main` now has SP0.1–SP4.2 + live-LLM tests (PR #3–#9 merged). This branch adds the **frontend chat panel** (+ chat message-id exposure); a fresh PR brings it in.

**Run the backend tests** (the venv pitfall: use the 3.12 venv, NOT system python):
```
cd munger/backend && TEST_DATABASE_URL=postgresql+psycopg://munger_app:Munger.App.2026@localhost:5432/munger_test \
  /Users/chuang/Documents/dev/projects/Munger/munger/backend/.venv/bin/python -m pytest tests/ -q -p no:cacheprovider \
  --ignore=tests/integration/test_provider_gate.py --ignore=tests/integration/test_frontend_smoke.py
```
Current: **178 passed** (the 2 ignored tests need OpenRouter creds / a built frontend).

**Live LLM tests** (opt-in, real OpenRouter — `tests/live/test_live_llm.py`, marker `live_llm`): exercise `LLMService.chat`/`chat_structured`/`embed_text` + `ChatService.ask` against a real model. Deselected from the default run (marked `integration`) and skip without a key. Run:
```
OPENROUTER_API_KEY=sk-or-... TEST_DATABASE_URL=…/munger_test \
  .../.venv/bin/python -m pytest tests/live -m live_llm -v
```
Optional: `LIVE_CHAT_MODEL` (default `deepseek/deepseek-v4-flash`), `LIVE_EMBED_MODEL` (default `qwen/qwen3-embedding-8b`, must be 768-dim). Defaults = the project's OpenRouter models; **verified 4/4 passing** against real OpenRouter.

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
| `2026-06-10-sp2.3b-community-reports.md` | ✅ DONE — `CommunityReportService`: per-community LLM title/summary + deterministic keyword label (mig 011) + `community_search` (ILIKE); `POST /api/communities/reports`, `GET /search` |
| `2026-06-10-sp3.1-retrieval.md` | ✅ DONE — `RetrievalService`: link + 3-channel (vector/lexical/graph-PPR) + RRF + salience rerank + assemble; `GET /api/search/retrieve` |
| `2026-06-10-sp3.2-retrieval-sharpening.md` | ✅ DONE — canonical-aware retrieval (COALESCE collapse) + vector seed-linking (existing entities HNSW, **no migration**) |
| `2026-06-10-sp4.1-chat-over-retrieval.md` | ✅ DONE — `ChatService.ask` (read-only RAG: retrieve→bridge `shortest_path`→synthesize→persist), `chat_sessions`/`chat_messages` (mig 012), `GraphService.shortest_path`, `POST /api/chat` + session/messages |
| `2026-06-10-sp4.2-feedback-writeback.md` | ✅ DONE — `FeedbackService` merge (labeled_pairs+resolve, reject also un-merges) / relate (`method='human'` relationship → edge rebuild) / rate (mig 013 `chat_messages.rating`); `POST /api/feedback/{merge,relate,rate}` |
| `2026-06-11-sp2.4-graph-gc.md` | ✅ DONE — `GraphGCService`: auto-prune orphans (never human-labeled) + HITL low-value candidates + safe delete (canonical roots refused); `GET /api/gc/candidates`, `POST /api/gc/{prune-orphans,delete}` |
| SP4.3 rating consumer (no SP doc) | ✅ DONE — chat 👍/👎 nudges retrieval rerank: bounded factor 1+0.1*clamp(net,±3), canonical-aware citation resolution; + worker phantom-healthcheck disable |
| `2026-06-11-extraction-windows.md` | ✅ DONE — extraction over K consecutive chunks/LLM call (INGEST_EXTRACTION_WINDOW_CHUNKS, default 1 = legacy; 2-3 recommended); demux to per-chunk rows preserves the reduce/mention/status contract; claimed-consecutive-run safety |
| `2026-06-11-streaming-chat.md` | ✅ DONE — SSE streaming chat: provider chat_stream (base fallback + OpenRouter SSE), ChatService.ask_stream (meta→delta→done, persist-at-end), POST /api/chat/stream, frontend streaming bubble w/ abort-on-switch |
| SP3.3 ranked community search (no SP doc) | ✅ DONE — generated tsvector + GIN (mig 014); community_search ts_rank-ordered w/ ILIKE fallback |
| multi-session chat (no SP doc) | ✅ DONE — backend list/delete sessions + auto-title from first message; frontend session rail (list/switch/new/delete, race-guarded) |
| frontend chat panel (no SP doc) | ✅ DONE — `/chat` route + `Chat.tsx` (markdown answers, citation chips → wiki, bridge path, 👍/👎 → `/api/feedback/rate`, localStorage session); backend exposes `assistant_message_id` + message `id`s |

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
- Retrieval (SP3.1 + SP3.2): `app/services/retrieval_service.py` (link + vector/lexical/graph-PPR + RRF + assemble; **SP3.2** canonical-aware collapse via `_canonical_map`/`_collapse` + vector seed-linking over the existing entities HNSW), `GraphService.personalized_pagerank`, `app/api/retrieval.py` (`GET /api/search/retrieve`), `RuntimeServices.retrieval`
- Resolution (SP2.2): `app/services/entity_resolution_service.py` (block/score/resolve/unmerge/label + `_flatten_chains`), `app/models/labeled_pair.py` (mig 010), `app/api/resolution.py`, `RuntimeServices.entity_resolution`
- Community reports (SP2.3b): `app/services/community_report_service.py` (generate_reports keywords+LLM summary, community_search), `app/api/communities.py`, `communities.title/summary/keywords` (mig 011), `RuntimeServices.community_report`
- Chat (SP4.1): `app/services/chat_service.py` (read-only RAG ask: retrieve→bridge→synthesize→persist + history), `GraphService.shortest_path`, `app/models/chat_session.py`/`chat_message.py` (mig 012), `app/api/chat.py` (`POST /api/chat` + sessions/messages), `RuntimeServices.chat`
- Graph GC (SP2.4): `app/services/graph_gc_service.py` (find_orphans/delete_entities/prune_orphans/gc_candidates; capture-then-NULL wiki order), `app/api/gc.py`, `RuntimeServices.gc`. Post-GC: re-run `/api/graph/recompute`
- Graph backfill: `app/api/graph.py` — `POST /api/graph/recompute?rebuild_edges=true` (EdgeService.rebuild_all + GraphService.recompute; the backfill entry point for pre-existing data)
- Feedback (SP4.2): `app/services/feedback_service.py` (merge: labeled_pairs+resolve, reject un-merges the pair; relate: human EntityRelationship→edge rebuild, service-level dedup; rate: ±1 on assistant turns, mig 013), `app/api/feedback.py`, `RuntimeServices.feedback`. Rating CONSUMER deferred (rerank boost later)

## Deferred / scale (per the txtai review)

`ingest_events` index trim (model-declared) · **model2vec** static embeddings (bulk-embed throughput) · vector **quantization** int8/binary (LanceDB) · **litellm** (replace hand-rolled multi-provider `LLMService`) · **smolagents** (SP4 chat agent) · Pathway/Ray (SP5).

## Conventions

- New ingest behavior stays behind a flag / additive; default `INGEST_ORCHESTRATOR=graph` unchanged.
- Migrations are **migration-only** (don't add new model-declared indexes — the project applies migrations incrementally on a persisted test DB; from-scratch `001` uses `create_all`).
- Per-SP: write plan → execute (subagent-driven, full review on SQL/logic-heavy tasks) → commit → push → PR per branch. (PR #3 was merged early at index-audit; SP3.1 + SP2.2 land via the next PR off `main`.)
