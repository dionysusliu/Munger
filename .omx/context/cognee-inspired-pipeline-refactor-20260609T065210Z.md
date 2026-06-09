# Context Snapshot: Cognee-inspired pipeline refactor

**Timestamp:** 2026-06-09T06:52:10Z  
**Task slug:** cognee-inspired-pipeline-refactor

## Task statement

Borrow architectural ideas from Cognee (`/Users/chuang/Documents/dev/projects/cognee`) to refactor Munger's backend ingestion pipeline. Cognee offers remember/recall/improve/delete APIs, RDB + GDB + VDB storage, and an add → cognify → improve data flow. Munger should explore how these map onto its LangGraph/LangChain runtime and scale the pipeline.

## Desired outcome

A refactored, scalable backend pipeline architecture informed by Cognee — with deep discussion on how each Cognee layer (API surface, multi-store infra, ingestion stages) helps Munger evolve beyond its current design.

## Stated solution (user ask)

- Study Cognee source as reference
- Adopt similar concepts: lifecycle APIs (remember/recall/improve/delete), tri-store (relational + graph + vector), staged ingestion (add → cognify → improve)
- Rebuild/refactor Munger pipeline using LangGraph/LangChain
- Focus on architecture discussion for scaling, not immediate implementation

## Probable intent hypothesis

User sees Munger's ingest path as reaching architectural limits (linear tool gating, wiki-centric outputs, Postgres-only graph) and wants a principled redesign before more incremental features. Cognee is a concrete reference for separating **ingest**, **cognify/graph build**, **retrieval**, and **feedback-driven improvement** — possibly to unify ingest, search, entities, and future agent memory under one mental model.

## Known facts / evidence (brownfield)

### Munger today
- **Ingest runtime:** LangGraph lead agent + `IngestToolGatingMiddleware` + SKILL.md (`default-ingest`)
- **Current 8-step pipeline** (`INGEST_TOOL_ORDER`): `parse_document` → `chunk_document` → `map_chunks` → `reduce_entities` → `summarize_source` → `generate_wiki_pages` → `link_wiki_pages` → `finalize_ingest`
- **Storage:** Postgres (SQLAlchemy) + pgvector migration `003_provenance_chunks_pgvector` (chunks, embeddings, entity relationships); source files on disk
- **No dedicated graph DB** — entities/mentions/relationships in Postgres tables; wiki is primary user-facing knowledge surface
- **API surface:** `/api/sources` (upload + ingest trigger), `/api/wiki`, `/api/entities`, `/api/search`, `/api/munger` (separate 12-dim path)
- **Async jobs:** `ingest_jobs` + worker poll; timeline via `ingest_events`
- **Recent work:** parallel map-reduce chunk extraction, contextual retrieval prefixes (in progress / partially landed per `.omx/context/parallel-chunk-map-reduce-contextual-*.md`)
- **ARCHITECTURE.md / WORKFLOW_ARCH.md** still describe legacy 5-tool pipeline in places — docs lag code

### Cognee reference (external repo)
- **Primary ECL flow:** `add` → `cognify` → `search` / `memify`
- **V2 memory API:** `remember`, `recall`, `improve`, `forget` — `remember` routes kwargs to add/cognify; `recall` unifies search types; `improve` enriches graph from feedback/sessions
- **Tri-store:** relational (SQLite/Postgres default), vector (LanceDB/PGVector), graph (Ladybug/Kuzu/Neo4j) via `get_*_engine()` factories
- **Pipeline tasks:** composable async tasks in `tasks/`, orchestrated by `run_pipeline()` in `modules/pipelines/`
- **Datasets:** multi-tenant scoping on add/cognify/search

### Rough conceptual mapping (hypothesis — needs user confirmation)
| Cognee | Munger today (possible analog) |
|--------|--------------------------------|
| `add` | upload source + `parse_document` / `chunk_document` |
| `cognify` | `map_chunks` + `reduce_entities` + wiki generation |
| `search` / `recall` | `/api/search`, entity/wiki browse |
| `improve` / `memify` | no equivalent; Munger 12-dim is separate |
| `delete` / `forget` | source delete; partial |
| RDB + VDB + GDB | Postgres + pgvector; no GDB |

## Constraints (stated or inferred)
- Keep LangGraph/LangChain as execution framework (user stated)
- Brownfield — existing UI, API clients, Postgres/Pigsty deployment
- Cognee repo is reference only — not a dependency fork requirement (unstated)

## Unknowns / open questions
- **Why now?** What concrete pain (scale, retrieval quality, operability, agent memory) drives refactor vs incremental evolution?
- **Scope:** API redesign only vs storage layer vs pipeline orchestration vs all three?
- **Graph DB:** adopt dedicated GDB (Kuzu/Neo4j) or stay Postgres-native graph tables?
- **remember/recall/improve:** first-class public API for Munger, or internal service layering only?
- **Wiki:** remain primary artifact or become one view over graph+vector store?
- **Relationship to recent map-reduce/contextual retrieval work** — preserve, replace, or reframe?
- **Breaking changes** acceptable for `/api/sources` ingest contract?

## Decision-boundary unknowns
- What OMX may decide without user confirmation (new DB engines, API versioning, delete legacy LangGraph agent loop)?
- Minimum viable refactor slice vs full Cognee-parity?

## Likely codebase touchpoints
- `munger/backend/app/runtime/` (agent, tools, middleware, pipeline_events)
- `munger/backend/app/services/` (chunk, extraction, resolution, search, wiki, provenance)
- `munger/backend/app/api/sources.py`, `search.py`, `entities.py`
- `munger/backend/app/models/` + alembic migrations
- `app/src/pages/Ingest.tsx`, `app/src/lib/api.ts`
- `ARCHITECTURE.md`, `WORKFLOW_ARCH.md`
