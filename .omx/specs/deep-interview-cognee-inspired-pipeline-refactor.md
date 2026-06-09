# Deep Interview Spec: Cognee-inspired pipeline refactor

## Metadata

| Field | Value |
|-------|-------|
| Profile | Standard |
| Rounds | 7 |
| Final ambiguity | **14%** (threshold 20%) |
| Context type | Brownfield |
| Interview ID | `0117091a-6e92-4be7-962c-2a17d2b22461` |
| Context snapshot | `.omx/context/cognee-inspired-pipeline-refactor-20260609T065210Z.md` |
| Transcript | `.omx/interviews/cognee-inspired-pipeline-refactor-20260609T075556Z.md` |
| Reference diagram | `ideas/ingestion-pipeline/Untitled-2026-06-05-1654.png` |
| Cognee source | `/Users/chuang/Documents/dev/projects/cognee` (pattern reference, not dependency) |

## Clarity breakdown

| Dimension | Score | Gap |
|-----------|-------|-----|
| Intent | 0.92 | Clear: simplify + unify ingest; scale via better reduce/linking |
| Outcome | 0.88 | Wiki-centric wikilinks + related pages |
| Scope | 0.90 | Detailed add/cognify subgraph spec; v1 single-file |
| Constraints | 0.85 | LangGraph, Postgres RDB+VDB, pdf/txt/md, chunks in DB |
| Success criteria | 0.55 | DB chunks confirmed; no perf/link-quality numeric SLA |
| Context (brownfield) | 0.90 | Current 8-tool pipeline + pgvector schema understood |

**Readiness gates:** Non-goals ✓ | Decision boundaries ✓ | Pressure pass ✓

---

## Intent (why)

Munger's current LangGraph ingest path (8 gated tools) is **too complex to extend** and does not adequately solve **cross-chunk entity resolution and linking**. Chunk/map volume is not the bottleneck — even large books yield few high-value concepts. The refactor should produce a **unified, staged ingestion architecture** inspired by Cognee's separation of concerns, while staying on **LangGraph subgraphs** and **Postgres-only storage** (relational + pgvector).

## Desired outcome

After ingest completes for a source:

1. **Per-chunk artifacts** exist: summaries, entity candidates, embeddings (pgvector), provenance in RDB.
2. **Reduce pass** deduplicates entities across chunks and establishes **credible cross-chunk relationships** (text mention, fuzzy match, semantic similarity — hybrid ranking).
3. **Entity wiki pages** are generated with **`[[wikilinks]]`** to related entities and a **related-pages** data model the frontend can render.
4. Pipeline is **orchestrated as LangGraph subgraphs** (`add`, `cognify`) in separate modules — not progressive LLM tool-gating.

## Cognee → Munger architecture mapping

| Cognee concept | Munger v1 mapping | Notes |
|----------------|-------------------|-------|
| `add()` | **`add` subgraph** — parse, register, content-hash dedup, dataset attach | Single-file upload only; no dir/S3 walk |
| `cognify()` | **`cognify` subgraph** — chunk, per-chunk map, aggregate reduce, wiki formulate | Cross-linking lives here (not separate improve in v1) |
| `improve()` / `memify()` | **Deferred** | User deferred Tavily/web enrichment; later pass if first-pass links insufficient |
| `remember()` / `recall()` | **Deferred** | No public lifecycle API in v1 |
| `delete()` / `forget()` | Existing source delete | No redesign required in v1 |
| RDB | Postgres (sources, entities, mentions, relationships, chunk metadata) | Keep |
| VDB | pgvector (`chunks.embedding`, summary vectors) | Keep |
| GDB | **Not adopted** | `entity_relationships` + `entity_mentions` are the graph; optional materialized view for read queries |
| `Task()` + `run_pipeline()` | **Pattern reference only** | Implementation uses LangGraph subgraphs, not Cognee task runner |
| Document / DocumentChunk | `Source` + `Chunk` ORM + file storage for raw uploads | Chunk **text stays in DB** (user override vs diagram) |

## In-scope (v1 slice)

### Orchestration

- Replace progressive `IngestToolGatingMiddleware` loop with **explicit LangGraph subgraphs**:
  - `add_subgraph` — ingestion registration
  - `cognify_subgraph` — chunk → map → reduce → wiki
- Subgraphs defined in **separate files** under `app/runtime/` (e.g. `graphs/add.py`, `graphs/cognify.py`).
- One LangGraph run per ingest job (worker invokes compiled parent graph).

### `add` subgraph

1. Accept **pdf, txt, md** (single file via existing upload path).
2. Parse to text; persist raw file + extracted text.
3. Compute **stable content hash**; skip or update on duplicate.
4. Register `Source` record (dataset scoping optional/future — not required v1).

### `cognify` subgraph

Per diagram (`Untitled-2026-06-05-1654.png`):

1. **Chunk** — section/chapter/paragraph/fixed-size (agent may choose algorithm).
2. **Per-chunk map (parallel)**:
   - Embed chunk → pgvector
   - LLM summarize chunk
   - Agent/tool extract entity candidates + intra-chunk relationships
   - Persist to RDB
3. **Aggregate reduce (sequential)**:
   - Gather all chunk outputs
   - Intra-chunk relations (confirm/normalize)
   - **Cross-chunk relations** — text mention search, fuzzy match, semantic embedding similarity, hybrid rank
   - **Entity resolution** — dedup/merge same entities across chunks
4. **Formulate wiki** — LLM generates entity wiki pages with references to related entities.
5. **Finalize** — index, status, events.

### Storage decisions (v1)

| Artifact | v1 location | Diagram note |
|----------|-------------|--------------|
| Raw upload | `DATA_DIR/sources/` | Unchanged |
| Chunk text + offsets + contextual prefix | **Postgres `chunks` table** (same instance as RDB) | Diagram FS/Lake — **overridden**; metadata + text in RDB |
| Embeddings | pgvector on `chunks` / `entities` (same Postgres, pgvector ext) | Logical "pg_vector" layer ≠ separate service |
| Entity/relationship metadata | Postgres RDB (same instance) | References = graph; no GDB |
| Wiki pages | Postgres (`wiki_pages`) + optional FS export | Aligned |

**Portability note (planning must address):** Document how chunk storage could migrate to FS/datalake later without rewriting cognify logic (e.g. content-addressed blob paths + RDB pointers).

## Out-of-scope / non-goals

- Dedicated graph database (Neo4j, Kuzu, etc.)
- Public `remember` / `recall` / `improve` / `delete` API surface
- Directory walk, S3 batch ingest, multi-format expansion (Cognee-full input matrix)
- Tavily / web / MCP enrichment
- Datalake file format for DocumentChunks in v1
- Cognee library as a runtime dependency

## Decision boundaries (agent may decide without confirmation)

- Postgres schema migrations (Alembic)
- Replace 8-tool gating with subgraph orchestration
- Chunking algorithm parameters
- Cross-chunk linking heuristics and thresholds
- Deprecate legacy tool aliases; update SKILL.md + tests
- Introduce `/api/v2` ingest with v1 compatibility shim

**Must follow:** Reference diagram flow and subgraph file separation.

## Constraints

- LangGraph + LangChain remain execution framework
- Postgres on Pigsty; pgvector required
- Single-file ingest trigger for v1
- Existing worker/job queue pattern (`ingest_jobs`, `ingest_events`) should be preserved or evolved with migration path

## Testable acceptance criteria

1. **Subgraph structure:** `add` and `cognify` are separate LangGraph subgraphs, compiled into parent ingest graph; no progressive tool-gating middleware on critical path.
2. **End-to-end ingest:** Upload pdf/txt/md → job completes → entity wiki pages exist with cross-entity wikilinks where chunks share entities.
3. **Reduce quality:** Integration test on fixed fixture corpus asserts merged entity count and ≥1 expected cross-chunk link (golden pairs TBD in planning).
4. **Chunk storage:** Full chunk text remains queryable from Postgres after ingest.
5. **Regression:** Existing pytest suite updated; `pytest tests/ -v` passes with `TEST_DATABASE_URL`.
6. **Observability:** `ingest_events` timeline reflects subgraph steps (not legacy 8-tool names).

## Assumptions exposed + resolutions

| Assumption | Resolution |
|------------|------------|
| Scale pain = chunk volume | **Rejected** — few chunks even for large books |
| Need GDB | **Rejected** — Postgres + pgvector sufficient |
| Cognee `improve` needed in v1 | **Deferred** — cross-linking in cognify reduce |
| Chunks in FS per diagram | **Rejected for v1** — keep in DB; plan portability |
| Keep LangGraph agent loop with tools | **Rejected** — explicit subgraph orchestration |

## Pressure-pass findings

- R2 deepened R1: "scale" means **reduce/linking design**, not parallel chunk throughput.
- User's Round 4 freeform superseded high-level Cognee API adoption — **subgraphs over lifecycle API**.

## Brownfield evidence

- Current pipeline: `INGEST_TOOL_ORDER` (8 steps) in `pipeline_events.py`
- Chunks ORM already stores full text + embeddings (`app/models/chunk.py`)
- Migration `003_provenance_chunks_pgvector` landed provenance schema
- Design doc: `ideas/ingestion-pipeline/munger-ingestion-pipeline-design.md` (tool decomposition, GraphRAG-inspired algorithms)

## Likely touchpoints

```
munger/backend/app/runtime/graphs/          # NEW: add + cognify subgraphs
munger/backend/app/runtime/agents/          # ingest_lead_agent → parent graph factory
munger/backend/app/runtime/tools/           # refactor to subgraph node callables
munger/backend/app/services/chunk_service.py
munger/backend/app/services/extraction_service.py
munger/backend/app/services/resolution_service.py
munger/backend/app/services/wiki_service.py
munger/backend/data/workflows/default-ingest/SKILL.md
munger/backend/tests/unit/test_*ingest*
app/src/pages/Ingest.tsx                    # if timeline/step labels change
ARCHITECTURE.md, WORKFLOW_ARCH.md
```

## Recommended execution handoff

Requirements are sufficiently clarified. **Do not implement in this interview.**

| Option | When |
|--------|------|
| **`$ralplan`** (recommended) | Architecture validation, subgraph design, linking algorithm options, datalake portability analysis |
| **`$autopilot`** | After plan approved — direct build |
| **`$ralph`** | Persistent loop until acceptance criteria met |
| **`$team`** | Parallel lanes (subgraphs + resolution + wiki + tests) |
| **Refine further** | If you want numeric perf SLA or golden link-quality corpus defined first |
