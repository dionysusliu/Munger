# RALPLAN: Cognee-inspired Pipeline Refactor — `add` + `cognify` Subgraphs

**Slug:** `cognee-inspired-pipeline-refactor`
**Spec:** `.omx/specs/deep-interview-cognee-inspired-pipeline-refactor.md`
**Context:** `.omx/context/cognee-inspired-pipeline-refactor-20260609T065210Z.md`
**Reference diagram:** `ideas/ingestion-pipeline/Untitled-2026-06-05-1654.png`
**Design doc:** `ideas/ingestion-pipeline/munger-ingestion-pipeline-design.md`
**Prior approved work:** `.omx/plans/ralplan-parallel-chunk-map-reduce-contextual.md` (8-tool MAP/REDUCE, shipped)
**Type:** Brownfield refactor — orchestration (agent+gating → StateGraph subgraphs) + **new cross-chunk linking**
**Mode:** Consensus (RALPLAN-DR + ADR) — Planner draft → Architect → Critic
**Date:** 2026-06-09
**Status:** APPROVED v2.2 — user amendments (Send map-reduce, references-as-graph, unified Postgres storage)
**References:** [LangGraph map-reduce (Suparna Guha, Medium)](https://medium.com/@welcome2suparna/from-theory-to-code-mastering-agentic-workflows-in-langgraph-part-2-scaling-with-map-reduce-f8331238a84a)

---

## Executive summary

The current ingest path is **functionally complete but architecturally a progressive-tool-gated LLM agent** (`langchain.create_agent` + `IngestToolGatingMiddleware`), not the explicit subgraph structure the user's diagram demands. The heavy lifting (chunk, map, reduce, wiki) already lives in **services** (`ChunkService`, `MapChunkService`, `ResolutionService`, `WikiService`); the agent merely calls them in a gated order.

Two distinct deliverables:

1. **Orchestration refactor (mechanical):** replace the agent+gating loop with two compiled **LangGraph `StateGraph` subgraphs** (`add`, `cognify`) composed into a parent ingest graph, invoked directly by `IngestRunner`. The proven service internals are reused as node bodies.
2. **Cross-chunk linking (genuinely new — the core pain):** today `ResolutionService.reduce_entities` does **only** `(name.lower(), normalized_type)` exact dedup. There is **no** fuzzy, semantic, or text-mention cross-chunk linking. `entities.embedding Vector(768)` exists in the schema but is **never populated**. A new `LinkingService` + `n_link` node implements a **text-mention + fuzzy + semantic hybrid** that produces credible cross-chunk relationships and feeds `[[wikilinks]]`.

Postgres-only (RDB + pgvector); chunks stay in DB (user override of diagram's FS/Lake); LangGraph/LangChain retained.

---

## Brownfield ground truth (verified, file-cited)

| Fact | Evidence |
|------|----------|
| Ingest is an **LLM agent**, not a StateGraph | `make_ingest_lead_agent` → `create_munger_agent` → `langchain.agents.create_agent` (`app/runtime/harness/factory.py:52`) |
| Driven by event stream, not graph invoke | `IngestRunner.run` uses `agent.astream_events(..., version="v2")` (`app/runtime/ingest_runner.py:120`) |
| **8-tool** canonical order | `INGEST_TOOL_ORDER` (`app/runtime/pipeline_events.py:26`): parse→chunk→map→reduce→summarize→generate_wiki→link_wiki→finalize |
| Progressive gating | `IngestToolGatingMiddleware.next_allowed_tool` (`app/runtime/harness/middlewares/ingest_tool_gating_middleware.py:50`) |
| Deprecated aliases live in tool list | `TOOL_ALIASES`, `COMPOSITE_ALIASES` (`pipeline_events.py:38-48`); alias bodies `pipeline_events`+`ingest_tools.py:125-133,288-299` |
| MAP already parallel | `MapChunkService.map_chunks` Wave A (`app/services/map_chunk_service.py:171-311`), semaphore = `ingest_chunk_worker_concurrency` (default 5) |
| **REDUCE is exact-dedup only** | `ResolutionService.reduce_entities` groups by `(name.lower(), etype)` (`app/services/resolution_service.py:107,151-155`); **no embedding / fuzzy / semantic** |
| `entities.embedding` exists but **unused** | model `app/models/entity.py:27`; column added in `003_provenance` (`alembic/versions/003_provenance_chunks_pgvector.py:90`); never written anywhere |
| chunk embeddings ARE populated + hnsw indexed | `map_chunk_service.py:287-300`; `ix_chunks_embedding_hnsw` (`003:101`) |
| Chunk text stays in Postgres | `Chunk.content Text` (`app/models/chunk.py:24`); confirms spec override of diagram |
| Provenance chain ready | `EntityMention.chunk_id/char_start/char_end` (`app/models/entity.py:52-56`); `ProvenanceService.get_provenance_chain` (`app/services/provenance_service.py:14`) |
| Cross-chunk relationships table exists | `EntityRelationship` quad-unique (`app/models/entity_relationship.py`); written intra-chunk only today (`resolution_service.py:197-227`) |
| No `app/runtime/graphs/` | only empty placeholders `app/runtime/graph/__init__.py`, `app/runtime/nodes/__init__.py` |
| Migration head | `003_provenance` (`alembic/versions/`) |
| Tests: no full-graph golden | unit only: `test_map_chunk_service.py`, `test_reduce_prof_merge.py`, `test_ingest_tool_gating.py`, `test_pipeline_events.py`, `test_chunk_service.py`, `test_ingest_agent.py`; `tests/integration/test_postgres_worker.py` is a **placeholder** (`:14`) |
| conftest discipline | `alembic upgrade head` once + per-test `TRUNCATE`; aborts if DB == `munger` (`tests/conftest.py`) |
| Config knobs | `ingest_chunk_size_tokens=600`, `overlap=100`, `max_gleanings=1`, `chunk_worker_concurrency=5`, `embedding_dimensions=768` (`app/core/config.py:43-46,39`) |
| ⚠️ **Docs stale** | `ARCHITECTURE.md:154-164` and `munger/backend/AGENTS.md` still describe the **5-tool** chain — must be corrected in this refactor |

**Planner note for Architect:** because services already implement chunk/map/reduce, the refactor risk is *not* re-implementing logic — it is (a) correctly wiring `StateGraph` + checkpointer + observability so the timeline/heartbeat semantics survive, and (b) the new linking algorithm's precision/recall. Bias effort accordingly.

---

## 1. RALPLAN-DR

### Principles

1. **Subgraphs are the contract, services are the engine.** `add`/`cognify` are explicit `StateGraph`s in separate files; node bodies delegate to existing services. No logic re-write where a service already exists.
2. **Cross-chunk linking is a first-class node, not a hidden side effect of reduce.** Merge (same entity) and relate (different entities, linked) are separated; both carry provenance.
3. **Provenance is never lost.** Every merge/link records contributing chunks + method + confidence (`entity_relationships` gains `confidence`/`method`); entity→mention→chunk→source chain preserved.
4. **Deterministic-testable linking.** Thresholds + scoring are pure functions; golden corpus runs under a scripted fake LLM + deterministic embeddings so CI is LLM-independent.
5. **Brownfield-safe.** One-release deprecation of gating + tool aliases; Postgres migrations are additive; `ingest_jobs`/`ingest_events`/heartbeat semantics preserved.

### Decision Drivers (top 3)

1. **Extensibility** — adding a stage today means editing `INGEST_TOOL_ORDER`, the gating middleware, the SKILL `tool-order`, and the alias map in lock-step (4 coupled edits). Subgraph edges localize change. *(spec Intent 0.92)*
2. **Cross-chunk resolution quality** — the explicit user pain: same entity across chunks/surface-forms must merge; related entities must link. Exact-name dedup cannot do this. *(spec Outcome §2, acceptance §3)*
3. **Diagram fidelity** — user diagram mandates `add`/`cognify` separation, parallel per-chunk map, an aggregate reduce with "relation across chunks / dedup-merge (text/semantic/hybrid)", and wiki formulate. *(spec "Must follow")*

### Viable options

#### A. Orchestration: StateGraph subgraphs vs keep agent+gating

**A1 — Full `StateGraph` subgraphs (CHOSEN).** Parent graph composes `add_subgraph` + `cognify_subgraph`; `IngestRunner` invokes the compiled parent via `.astream()`.
- *Pros:* deterministic edges (no LLM tool-routing variance); matches diagram; cheaper (no per-step model call just to pick the next tool); per-node retry/conditional edges; `add`/`cognify` independently testable; removes gating middleware from critical path (acceptance §1).
- *Cons:* lose the "agent autonomy" narrative; must re-home observability (`pipeline_step`, heartbeat, `agent_message`/`tool_call` events) from agent stream to node wrappers; checkpointer thread/resume semantics need re-validation.

**A2 — Keep `create_agent` + gating, just rename steps (REJECTED).**
- *Pros:* smallest diff; observability untouched.
- *Cons:* violates spec "Rejected — explicit subgraph orchestration" and "Must follow … subgraph file separation"; keeps the 4-edit coupling; LLM still burns a turn per step. **Fails acceptance §1.**

**A3 — Hybrid: StateGraph parent, `map` stays an agent (NOT CHOSEN, fallback).** Parent is a graph but the per-chunk extraction remains agentic.
- *Pros:* keeps any agentic gleaning flexibility.
- *Cons:* two orchestration paradigms; `MapChunkService` is already deterministic+parallel, so agentizing it is a regression. Keep as escape hatch only if Send-based fan-out (below) proves unstable.

> **`map` fan-out sub-decision (v2.2 — CHOSEN):** adopt LangGraph **`Send` scatter-gather** per [Medium map-reduce pattern](https://medium.com/@welcome2suparna/from-theory-to-code-mastering-agentic-workflows-in-langgraph-part-2-scaling-with-map-reduce-f8331238a84a): `fanout_chunks` → `Send("process_chunk", …)` per chunk → `chunk_map_subgraph` wrapper → `Annotated[..., merge_dicts]` reducer → `n_reduce`. `MapChunkService.map_single_chunk` becomes the per-chunk worker body (extract from today's `map_chunks` loop). Service-internal `asyncio.gather` is **retired** once Send path is green; keep behind `INGEST_MAP_MODE=service|send` flag during migration.

#### B. Cross-chunk linking algorithm

**B1 — Semantic-only (pgvector cosine on entity embeddings) (REJECTED alone).**
- *Pros:* trivial with existing pgvector; catches paraphrase.
- *Cons:* short proper nouns embed poorly; over-merges sibling concepts ("System 1" vs "System 2"); non-deterministic to test.

**B2 — Lexical/fuzzy-only (rapidfuzz + `pg_trgm`) (REJECTED alone).**
- *Pros:* deterministic, cheap, great for surface variants ("Munger" ↔ "Charlie Munger").
- *Cons:* misses cross-lingual aliases (design doc requires zh/en, `munger-ingestion-pipeline-design.md` GLEAN_PROMPT) and paraphrased concepts.

**B3 — Hybrid: text-mention + fuzzy + semantic with weighted score and gated LLM adjudication (CHOSEN).** Detailed in §4.
- *Pros:* best recall×precision; type-gated to prevent cross-type merges; deterministic core with optional LLM only in the gray zone; produces both *merges* and *related links*; aligns exactly with diagram's "text-based/semantic/hybrid rank".
- *Cons:* threshold tuning; more code; needs golden corpus to lock behavior.

#### C. Chunk storage portability

**C1 — Postgres `chunks.content TEXT` (CHOSEN v1).** Unchanged from today (`models/chunk.py:24`).
- *Pros:* user override; full-text queryable (acceptance §4); zero migration churn.
- *Cons:* large books bloat the row store.

**C2 — Content-addressed blob now (REJECTED).** Premature; spec non-goal "Datalake file format … in v1".

> **Portability pattern (planned, not built) — see §8:** add nullable `content_uri` + `content_sha256` to `chunks`; a `ChunkContentResolver` reads blob when `content_uri` set, else DB `content`. Lets a later migration move text to FS/Lake without touching `cognify` logic.

---

## 2. PRD

### Problem
Munger's ingest is hard to extend (coupled tool-order/gating/skill/alias edits) and **cannot resolve or link entities across chunks** beyond exact name+type match. Same-entity variants stay split; genuinely related entities never get linked; wiki `[[wikilinks]]`/related-pages are therefore thin. The `entities.embedding` column sits unused.

### Goals
1. Replace agent+gating critical path with explicit, file-separated `add` + `cognify` LangGraph subgraphs compiled into a parent graph invoked by the worker.
2. Implement a credible **cross-chunk linking** stage (text-mention + fuzzy + semantic hybrid) producing entity **merges** and **related-links**, both with provenance + confidence.
3. Populate and use `entities.embedding`; emit `[[wikilinks]]` + related-page links (`WikiLink`) from linked entities.
4. Preserve Postgres-only storage, chunk-text-in-DB, observability (`ingest_events` timeline + heartbeat), and job-queue semantics.
5. Keep docs (`ARCHITECTURE.md`, AGENTS.md tree, SKILL.md) truthful.

### Non-goals (from spec §"Out-of-scope")
Dedicated graph DB; public `remember`/`recall`/`improve`/`delete` API; directory/S3 batch; multi-format beyond pdf/txt/md; Tavily/web/MCP enrichment; datalake file format for chunks in v1; Cognee as a runtime dependency; numeric perf SLA.

### User stories (right-sized: 6)
1. **Operator** uploads a pdf/txt/md and the ingest job completes with status visible via existing `GET /api/sources/{id}/status`.
2. **Reader** sees an entity wiki page whose `[[wikilinks]]` point to related entities discovered across different chunks.
3. **Reader** opens a "related pages" panel backed by `WikiLink` rows generated from cross-chunk links.
4. **Curator** re-uploads the same document and it is content-hash-deduped (no duplicate Source/entities).
5. **Maintainer** adds a new cognify stage by inserting one node + one edge, without editing a gating middleware.
6. **Maintainer** runs `pytest tests/ -v` and a golden-corpus integration test asserts merged-entity count and ≥1 expected cross-chunk link, deterministically.

---

## 3. Architecture

### 3.1 Graph composition

```
IngestRunner.run(source_id, job_id)
  └─ build_ingest_graph(services)  →  compiled parent StateGraph (Postgres checkpointer)
        ├─ add_subgraph        (app/runtime/graphs/add.py)
        │     register → parse → hash_dedup ─(duplicate?)→ skip_cognify → END
        │                                   └(new)──────→ cognify_subgraph
        └─ cognify_subgraph    (app/runtime/graphs/cognify.py)
              chunk → fanout_map (Send) → reduce → link → summarize → wiki → finalize → END
                    └─ chunk_map_subgraph (per chunk, parallel)
```

### 3.2 `add` subgraph nodes

| Node | Body (delegates to) | Effect | Replaces |
|------|---------------------|--------|----------|
| `n_register` | `db_helpers.update_source_status` | status→`extracting`; ensure Source | (part of) `parse_document` |
| `n_parse` | `StorageService.extract_text` (`ingest_tools.py:79`) | raw file → `sources.content_text` (cache-aware) | `parse_document` |
| `n_hash_dedup` | query existing `Source.content_hash` (`models/source.py:19`) | **re-ingest/backfill only** — normal upload already 409s at API (`sources.py:103-111`) | guard for worker-triggered re-ingest |
| `n_skip` | mark job+source | duplicate re-ingest: `source.status=skipped_duplicate`, `job.status=completed`, emit `duplicate_of_source_id`, **no cognify** | worker/backfill only |
| conditional edge | — | duplicate → `n_skip` else → cognify | — |

### 3.3 `cognify` subgraph nodes

| Node | Body (delegates to) | Status | Notes |
|------|---------------------|--------|-------|
| `n_chunk` | `ChunkService.split_chunks` (`chunk_service.py:103`) | reuse | token split, no LLM |
| `n_fanout_map` | `fanout_chunks` dispatcher | **NEW** | emits `Send("process_chunk", {chunk_id, …})` per chunk (LangGraph map) |
| `n_process_chunk` | wrapper → `chunk_map_subgraph` | **NEW** | per-chunk: prefix+extract+glean+embed via `MapChunkService.map_single_chunk` |
| `chunk_map_subgraph` | compiled `StateGraph(ChunkMapState)` | **NEW** | isolated per-chunk state; returns metrics dict merged by reducer |
| `n_reduce` | `ResolutionService.reduce_entities` (`resolution_service.py:80`) | reuse | exact dedup, prof-merge, mentions, intra-chunk rels |
| `n_link` | **new** `LinkingService.link_source` | **NEW** | text-mention + fuzzy + semantic hybrid → merges + cross-chunk `related` links + populate `entities.embedding` |
| `n_summarize` | `LLMService.summarize` (`ingest_tools.py:134`) | reuse | non-fatal |
| `n_wiki` | `generate_wiki_pages` + `link_wiki_pages` | reuse+extend | **two** `pipeline_step` emissions (`generate_wiki_pages`, `link_wiki_pages`) inside one node — matches `GRAPH_STEP_ORDER` |
| `n_finalize` | `finalize_ingest` (`ingest_tools.py:260`) | reuse | index, status→completed, `pipeline_summary` |

> `n_map` and `n_reduce` map 1:1 onto the diagram's "from chunk1..N → embeddings/pg_vector + list of entities + summary" and "gather results from ALL processed chunks". `n_link` is the diagram's three middle boxes ("relations in same chunk" [from reduce], "relation across different chunks", "dedup/merge same entities across chunks").

### 3.4 State schema (`app/runtime/graphs/state.py`)

```python
from typing import Annotated, TypedDict

def merge_dicts(left: dict, right: dict) -> dict:
    merged = left.copy()
    merged.update(right)
    return merged

class AddState(TypedDict, total=False):
    source_id: int
    job_id: int | None
    file_path: str
    file_type: str
    content_text: str
    is_duplicate: bool
    duplicate_of_source_id: int | None
    # content_hash lives on Source row — do not duplicate in state

class ChunkMapState(TypedDict, total=False):
    """Isolated per-chunk subgraph state (Send pattern)."""
    source_id: int
    job_id: int | None
    chunk_id: int
    map_result: dict           # entities_raw, glean_*, prefix_chars

class CognifyState(TypedDict, total=False):
    source_id: int
    job_id: int | None
    chunk_ids: list[int]
    map_metrics: Annotated[dict, merge_dicts]  # reducer merges per-chunk Send results
    reduce_metrics: dict       # entities_canonical, mentions_created, prof_merges
    link_metrics: dict         # merges, cross_chunk_links, method counts
    summary_chars: int
    wiki_metrics: dict
    error: str | None
    status: str

class IngestState(AddState, CognifyState, total=False):
    """Parent channel = union; subgraphs read/write their slice."""
```

Reuse/retire: current `app/runtime/state.py:IngestRunState` is the agent return shape — keep `IngestRunner` returning a compatible dict (`source_id`, `status`, `thread_id`) for worker compatibility (`ingest_runner.py:165`).

### 3.5 File layout (NEW under `munger/backend/`)

```
app/runtime/graphs/
├── __init__.py
├── state.py              # AddState, CognifyState, IngestState
├── add.py                # build_add_subgraph(services) -> StateGraph
├── cognify.py            # build_cognify_subgraph(services) -> StateGraph
├── ingest.py             # build_ingest_graph(services, checkpointer) -> compiled parent
└── nodes/
    ├── __init__.py
    ├── add_nodes.py       # register, parse, hash_dedup, skip
    ├── cognify_nodes.py   # chunk, fanout_map, process_chunk, reduce, link, summarize, wiki, finalize
    └── chunk_map.py       # build_chunk_map_subgraph() — per-chunk Send worker
app/services/
└── linking_service.py     # NEW: CrossChunkLinkingService (§4)
app/runtime/
├── ingest_runner.py       # MODIFY: invoke compiled parent graph instead of agent
├── pipeline_events.py     # KEEP step events; INGEST_TOOL_ORDER → step keys for timeline parity
└── graph_observability.py # NEW (optional): node wrapper to emit pipeline_step + heartbeat
```

Each node body wraps its work in the existing `pipeline_step(...)` async context (`pipeline_events.py:140`) so the `ingest_events` timeline and `pipeline_summary` survive unchanged for the frontend (acceptance §6).

### 3.6 Map-reduce scatter-gather (LangGraph `Send`)

Reference implementation follows [Suparna Guha's LangGraph map-reduce pattern](https://medium.com/@welcome2suparna/from-theory-to-code-mastering-agentic-workflows-in-langgraph-part-2-scaling-with-map-reduce-f8331238a84a):

```
n_chunk  →  n_fanout_map  ──Send("process_chunk")──┐  (parallel)
                      │                            ├→ n_process_chunk → chunk_map_subgraph
                      │                            │
                      └── all complete ────────────┘
                                    ↓
                              n_reduce (gather)
```

| Component | Role |
|-----------|------|
| `fanout_chunks(state)` | Returns `list[Send]` — one per `chunk_id` |
| `process_chunk` wrapper | Translates parent state → `ChunkMapState`, invokes subgraph, returns `{map_metrics: {chunk_id: result}}` |
| `Annotated[dict, merge_dicts]` | LangGraph reducer combines per-chunk metrics before `n_reduce` |
| `chunk_map_subgraph` | Isolated `ChunkMapState`: prefix → extract → glean → embed → persist |

**Edge contract:** `add_conditional_edges("n_chunk", fanout_chunks)` triggers map; edge `process_chunk → n_reduce` is the reduce barrier (LangGraph waits for all Send tasks).

**Migration:** extract `map_single_chunk(chunk_id, …)` from `MapChunkService.map_chunks` loop; `INGEST_MAP_MODE=send|service` toggles Send vs legacy gather during Phase 4.

### 3.7 Storage topology — unified Postgres (explicit ADR)

The diagram's **pg_vector** and **pg_rdb** are **logical layers on one Postgres instance**, not separate services. Pigsty already runs Postgres with **pgvector** enabled — zero additional infra.

| Layer (diagram) | Munger v1 physical store | Table / column |
|-----------------|--------------------------|----------------|
| pg_rdb | Same Postgres | `sources`, `chunks` (metadata), `entities`, `entity_mentions`, `entity_relationships`, `wiki_pages` |
| pg_vector | Same Postgres (pgvector ext) | `chunks.embedding`, `entities.embedding` |
| DocumentChunks (diagram FS/Lake) | **Postgres `chunks.content` TEXT** — **not FS** | `source_id`, `chunk_index`, `doc_char_start/end`, `token_count`, `content` |

**Rationale (user decision):** chunk metadata + raw text in RDB keeps provenance queries simple (`chunk → mention → entity → source` in one SQL join). Pure FS/Lake for chunk bodies makes provenance painful. Embeddings stay in-vector columns on the same rows.

**Future portability (optional, not v1):** nullable `chunks.content_uri` lets text move to blob storage later; metadata + embedding remain in Postgres. See §8.

### 3.8 Graph-as-query — no explicit graph store

**No GDB. No separate graph data model.** The "graph" is the extracted references we already persist:

- **Nodes** → `entities` (+ optional `wiki_pages`)
- **Edges** → `entity_relationships` (with `confidence`, `method`, `source_id`, `chunk_id` provenance)
- **Evidence** → `entity_mentions` (chunk offsets)

For read/query surfaces (future Graph UI, related-pages API), two options — **both v1-compatible:**

1. **Ad-hoc SQL** — join `entities` ↔ `entity_relationships` ↔ `entity_mentions` ↔ `chunks` on demand.
2. **Materialized view** (preferred for Graph page) — e.g. `entity_graph_edges` refreshed after ingest:

```sql
CREATE MATERIALIZED VIEW entity_graph_edges AS
SELECT er.id, er.source_entity_id AS from_id, er.target_entity_id AS to_id,
       er.relationship_type, er.confidence, er.method, er.source_id
FROM entity_relationships er;
-- REFRESH MATERIALIZED VIEW CONCURRENTLY after finalize_ingest
```

No Neo4j/Kuzu, no Cognee-style graph engine factory. Wiki `[[wikilinks]]` and related-pages read from the same reference tables.

**Timeline registry (fixes C2):** extend `INGEST_TOOL_ORDER` + `STEP_LABELS` to include new graph steps:

```python
GRAPH_STEP_ORDER = [
    "register_source", "parse_document", "hash_dedup",
    "chunk_document", "map_chunks", "reduce_entities", "link_entities",
    "summarize_source", "generate_wiki_pages", "link_wiki_pages", "finalize_ingest",
]
```

- `register_source`, `hash_dedup`, `link_entities` are **new labeled steps** (frontend `Ingest.tsx` timeline will show them).
- Legacy alias names remain mapped via `canonical_tool_name` for one release.
- `step_total` derives from `len(GRAPH_STEP_ORDER)`.

---

## 4. Cross-chunk linking design (the core)

New `app/services/linking_service.py` invoked by `n_link`, **after** `reduce_entities` has produced canonical `entities` + provenance `entity_mentions` for the source.

Inputs available: canonical `Entity` rows (name, type, description), per-source `EntityMention` (chunk_id, offsets), `chunks.content` + `chunks.embedding` (populated), full `sources.content_text`.

### Stage R-EMB — Entity embedding (fills the unused column)
Batch-embed `"{name}: {description}"` for this source's affected entities via `LLMService.embed_texts` (`llm_service.py:507`); write `entities.embedding` (`models/entity.py:27`). Enables semantic blocking. *(First time this column is ever written.)*

### Stage R-TEXT — Text-mention augmentation (the "text-based" leg)
For each canonical entity, build a surface-form set = {name} ∪ alias variants (case-insensitive; acronym of multiword name; configured zh/en alias if present in description). Scan **all** chunks of the source (`chunks.content`, regex word-boundary, `re.escape`, IGNORECASE — mirrors `ingest_tools.py:245`) for occurrences the extractor missed. Each hit with no existing mention in that chunk → add `EntityMention(chunk_id, char_start/end via offset)`. This raises recall of provenance and seeds cross-chunk co-occurrence without an LLM call. Bounded by entity count × chunk count (small per spec Intent §"few high-value concepts").

### Stage R-CAND — Candidate pair generation (blocking) — **within-source v1 (C3)**
Generate candidate entity pairs **only among entities with ≥1 `EntityMention` in the current `source_id`**. Global fuzzy/semantic merge is **deferred** (Open Q4). `reduce_entities` already does exact-name global lookup (`resolution_service.py:149-155`); linking must not add destructive global merges in v1.

Three cheap blockers, **type-gated** (never pair incompatible `entity_type`):
- **Lexical:** `pg_trgm` similarity on `entities.name` ≥ `link_fuzzy_trgm` (SQL `similarity()`), plus rapidfuzz `token_set_ratio` ≥ `link_fuzzy_ratio` (default 90) computed in Python for the trgm shortlist.
- **Semantic:** pgvector cosine on `entities.embedding` ≤ distance `link_semantic_dist` (default cosine ≥ 0.83) via hnsw index (new, §5).
- **Co-mention:** entities sharing ≥1 chunk (from R-TEXT/mentions) → candidates for *relate* (not merge).

### Stage R-SCORE — Hybrid score + decision
For each candidate pair compute:
```
lexical  = max(trgm_sim, rapidfuzz_ratio/100)         # 0..1
semantic = cosine_similarity(emb_a, emb_b)            # 0..1
score    = w_lex*lexical + w_sem*semantic             # default w_lex=0.45, w_sem=0.55
```
Decision ladder (type must match for MERGE):
| Condition | Action |
|-----------|--------|
| `score ≥ link_auto_merge` (0.92) **and** same type | **MERGE** (auto) |
| `link_review_low` (0.80) ≤ `score` < auto **and** same type | **LLM adjudication** (cheap YES/NO, reuse `PROF_MERGE_SYSTEM`-style gate) → MERGE if YES else RELATE |
| candidate via co-mention or `score` in [0.70, review_low) | **RELATE** — create `EntityRelationship(type="related", method, confidence=score)` |
| below 0.70 | discard |

### Stage R-MERGE — Apply merges (within-source only)
Merge loser→winner (winner = higher `mention_count` **within this source**, tie → lower id). **v1 guard:** refuse to delete an entity that has mentions from a different `source_id`.

Repoint with conflict handling (K2): `EntityMention` upsert on `(entity_id, chunk_id)`; `EntityRelationship` repoint uses delete-then-insert or `ON CONFLICT DO NOTHING` on quad-unique `(source_entity, target_entity, relationship_type, source_id)`.

**Idempotency (C4):** `n_link` delete-first, scoped to this source:
1. `EntityRelationship` where `method IN ('lexical','semantic','hybrid','co_mention','llm')` and supporting `source_id`
2. R-TEXT mentions tagged `mention_method='link_text'` for this source
3. Recompute from immutable inputs (`ChunkExtraction` + chunks) — never resume mid-merge on a partially deleted global entity set

Record merge decisions in a `link_decisions` JSON artifact on `IngestJob` or a `source_link_runs` table before applying destructive merges (enables resume audit).

### Stage R-LINK — Cross-chunk relationships
Persist RELATE decisions as `EntityRelationship(relationship_type="related", source_id, chunk_id=<a supporting chunk>, description=<method+score>)` with **new** `confidence FLOAT` + `method VARCHAR` columns (§5) for observability and golden-test assertions.

### Stage R-WIKI handoff
`n_wiki` reads merged entities + `related` relationships and:
- writes `[[Target Name]]` wikilinks into the entity page body (LLM prompt already supports, `ingest_tools.py:197`),
- creates `WikiLink(link_type="related")` rows so the frontend related-pages panel renders (reuses `WikiService.create_link`, `ingest_tools.py:249`).

### Tunables (add to `app/core/config.py`, defaults shown)
`INGEST_LINK_FUZZY_RATIO=90`, `INGEST_LINK_TRGM=0.45`, `INGEST_LINK_SEMANTIC_COSINE=0.83`, `INGEST_LINK_W_LEX=0.45`, `INGEST_LINK_W_SEM=0.55`, `INGEST_LINK_AUTO_MERGE=0.92`, `INGEST_LINK_REVIEW_LOW=0.80`, `INGEST_LINK_RELATE_MIN=0.70`, `INGEST_LINK_LLM_ADJUDICATE=true`.

New deps (light, per design doc §1): `rapidfuzz`. `pg_trgm` is a Postgres extension (CREATE EXTENSION in migration). pgvector already present.

---

## 5. Migration plan

### 5.1 Orchestration migration (agent → subgraphs)
**Release N (introduce, dual-safe):**
1. Add `app/runtime/graphs/*` (subgraphs + parent) behind a settings flag `INGEST_ORCHESTRATOR` ∈ {`graph`(default), `agent`}.
2. `IngestRunner.run` branches: `graph` → `build_ingest_graph(...).astream(...)`; `agent` → existing path (rollback escape hatch).
3. Node bodies reuse service calls; wrap in `pipeline_step` so timeline/heartbeat identical.
4. SKILL.md: `default-ingest/SKILL.md` retained as the **prompt/quality reference** only; `tool-order` frontmatter becomes documentation (graph edges are authoritative). Update body to describe subgraph stages.

**Release N+1 (deprecate gating):**
5. Remove `IngestToolGatingMiddleware` from `build_ingest_middleware_chain` (`factory.py:37`) once `graph` is default and validated; keep the middleware file one release with a deprecation log.
6. Retire deprecated tool aliases (`extract_source_text`, `extract_entities_from_text`, `create_wiki_pages`, `extract_entities_from_chunks`, `glean_entities`, `resolve_entities`) from `build_ingest_tools` (`ingest_tools.py:319-327`) and `TOOL_ALIASES`/`COMPOSITE_ALIASES` (`pipeline_events.py:38-48`). Update `test_ingest_tool_gating.py` (delete or repoint).

**API:**
- `/api/v2` ingest is **optional** and deferred. v1 surface (`POST /api/sources/{id}/ingest` → 202 + `job_id`; `GET …/status`) is unchanged because orchestration is internal to the worker. **No v2 needed for v1 slice** — record as ADR (avoid scope creep). Compatibility shim only if a future change alters request/response shape.

### 5.2 Schema migration `004_cross_chunk_linking` (additive)
```
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE INDEX ix_entities_name_trgm ON entities USING gin (name gin_trgm_ops);
CREATE INDEX ix_entities_embedding_hnsw ON entities USING hnsw (embedding vector_cosine_ops);  -- column exists since 003, never indexed
ALTER TABLE entity_relationships
    ADD COLUMN confidence DOUBLE PRECISION,
    ADD COLUMN method VARCHAR(20);   -- 'lexical'|'semantic'|'hybrid'|'co_mention'|'llm'
ALTER TABLE entity_mentions
    ADD COLUMN mention_method VARCHAR(20) DEFAULT 'extract';  -- 'extract'|'link_text'
-- portability (planned, nullable now; see §8)
ALTER TABLE chunks
    ADD COLUMN content_uri VARCHAR(512);
-- NOTE: sources.content_hash already exists (source.py:19); do NOT add chunks.content_sha256
-- collapse duplicate (entity_id, chunk_id) in reduce before insert; then:
CREATE UNIQUE INDEX IF NOT EXISTS uq_entity_mentions_entity_chunk ON entity_mentions(entity_id, chunk_id);
```
Down-migration drops the above. No data backfill required (new sources populate; existing sources re-ingest via existing backfill path). `_require_pgvector()` guard pattern reused from `003`.

### 5.3 Docs migration (truth-up)
- `ARCHITECTURE.md` §"Ingest pipeline" (currently 5 tools, `:154-164`) → subgraph diagram.
- `munger/backend/AGENTS.md` "Ingest tools (strict order)" + "Active skill" → subgraph description.
- `munger/backend/WORKFLOW_ARCH.md` → note skill is reference, graph is authoritative.

---

## 6. Test spec

### 6.1 Determinism harness (prerequisite)
`tests/fixtures/fake_llm.py` — `ScriptedLLMService` implementing `chat`, `embed_texts`, `summarize`, `generate_wiki_page`:
- `chat` returns canned `ExtractionResult`/`GleanResult`/YES-NO JSON keyed by chunk content hash.
- `embed_texts` returns **deterministic** vectors (e.g. seeded hash → unit-normalized 768-dim) so cosine is reproducible and golden thresholds are stable.
Inject via `RuntimeServices(llm=ScriptedLLMService())`.

### 6.2 Unit
| Test file | Asserts |
|-----------|---------|
| `tests/unit/test_linking_service.py` (NEW) | scoring ladder pure-fn: lexical/semantic/hybrid boundaries; type-gate blocks cross-type merge; merge repoints mentions+relationships; idempotent re-run |
| `tests/unit/test_add_subgraph.py` (NEW) | register→parse→hash_dedup; duplicate short-circuits to `n_skip`; reuses `Source.content_hash` |
| `tests/unit/test_cognify_subgraph.py` (NEW) | node order; `n_map`/`n_reduce` delegate to services; error in `n_parse` fails source |
| extend `test_reduce_prof_merge.py` | reduce still exact-dedups; link stage is additive (no double-merge) |
| update `test_ingest_tool_gating.py` | repoint or remove at Release N+1 |
| update `test_pipeline_events.py` | step keys still emit for subgraph nodes |

### 6.3 Integration (replace placeholder `tests/integration/test_postgres_worker.py:14`)
| Test | Asserts |
|------|---------|
| `test_ingest_graph_end_to_end` | upload txt → `build_ingest_graph` run → source `completed`; chunks queryable from Postgres (acceptance §4); `ingest_events` contains subgraph step events not legacy 8-tool names (§6) |
| `test_add_dedup` | re-ingest same content → no duplicate Source/entities |

### 6.4 Two-tier link validation (C5)

**Tier A — CI structural golden** (`test_cross_chunk_golden.py`): uses `ScriptedLLMService` with **hand-rigged embedding pairs** per fixture entity. Asserts plumbing only: scoring ladder, merge repoint, relationship rows, wikilink emission, negative precision guard. **Does not claim semantic recall quality.**

**Tier B — non-CI eval harness** (`tests/eval/test_linking_quality.py`): real `embed_texts`, labeled pairs in `tests/fixtures/golden/expected.json`, emits precision/recall report (not a CI gate). Phase 8 deliverable.

### 6.5 Golden corpus (structural — Tier A)
`tests/fixtures/golden/` — 3 hand-built `.txt` docs engineered so a known entity recurs across ≥2 chunks under variant surface forms, plus a known related pair:
- `munger_circle.txt`: "Charlie Munger" (chunk 1) / "Munger" (chunk 2) / "查理·芒格" (chunk 3) → **1 canonical entity, 3 mentions across 3 chunks**.
- `mental_models.txt`: "circle of competence" + "latticework of models" co-occur across chunks → **≥1 `related` link**.
- `negative.txt`: "System 1" vs "System 2" → **must NOT merge** (type same, score below auto; precision guard).

`tests/integration/test_cross_chunk_golden.py` (NEW) runs full `cognify` under `ScriptedLLMService` with `INGEST_LINK_LLM_ADJUDICATE=false` and rigged embeddings (scores outside gray zone) and asserts:
1. `entities` count == expected merged count (e.g. exactly 1 "Charlie Munger").
2. `entity_mentions` for that entity span ≥2 distinct `chunk_id`.
3. ≥1 `entity_relationships` with `relationship_type="related"` and `method in {hybrid,semantic,co_mention}` for the expected pair.
4. negative pair NOT merged (2 distinct entities remain).
5. resulting wiki page body contains the expected `[[wikilink]]` and a `WikiLink(link_type="related")` row exists.

Golden expectations stored as `tests/fixtures/golden/expected.json` so Architect/Critic can adjust thresholds against fixed truth.

### 6.6 Resume + fallback tests (K3)
| Test | Asserts |
|------|---------|
| `test_ingest_graph_resume_after_link_failure` | kill after `n_reduce`, resume completes; no duplicate R-TEXT mentions |
| `test_ingest_orchestrator_agent_fallback` | `INGEST_ORCHESTRATOR=agent` still completes (rollback path) |

### 6.7 Regression gate
`pytest tests/ -v` with `TEST_DATABASE_URL` → `munger_test` (acceptance §5); conftest `alembic upgrade head` picks up `004` automatically.

---

## 7. Implementation steps (9 phases, dependency-ordered)

1. **Schema + deps.** Add `004_cross_chunk_linking`; add `rapidfuzz` to `pyproject.toml`; add link tunables + `INGEST_ORCHESTRATOR` to `config.py`. Verify `alembic upgrade head` on `munger_test`.
2. **State + graph scaffolding.** `app/runtime/graphs/state.py`, empty `add.py`/`cognify.py`/`ingest.py` builders + `nodes/`. Compile-only smoke test.
3. **`add` subgraph.** Implement `n_register`/`n_parse`/`n_hash_dedup`/skip using existing `Source.content_hash`. Unit test re-ingest dedup (not upload 409 — K1). Remove empty `app/runtime/graph/` + `app/runtime/nodes/` placeholders (C6).
4. **`cognify` subgraph + Send map-reduce.** Wire `n_chunk` → `fanout_chunks` → `process_chunk`/`chunk_map_subgraph` → `n_reduce` (reduce barrier); extract `map_single_chunk` from `MapChunkService`. `INGEST_MAP_MODE=send`. E2E integration test (no linking yet) green.
5. **`LinkingService` core.** R-EMB + R-CAND + R-SCORE + R-MERGE + R-LINK; pure-fn unit tests (no DB) for the scoring ladder first, then DB-backed.
6. **`n_link` node + R-TEXT augmentation + wiki wikilink/related emission.** Extend `n_wiki` to consume relationships.
7. **`IngestRunner` switch.** Branch on `INGEST_ORCHESTRATOR` (default `graph`); invoke compiled parent; preserve return dict + status events. Keep agent path behind flag.
8. **Golden corpus + integration suite.** Build fixtures + `ScriptedLLMService`; land `test_cross_chunk_golden.py`, replace worker placeholder; full `pytest -v`.
9. **Deprecate + docs.** (Release N+1) remove gating from middleware chain + retire aliases + repoint gating test; rewrite `ARCHITECTURE.md`/AGENTS.md/SKILL.md/WORKFLOW_ARCH.md; update `Ingest.tsx` timeline for 3 new steps (`register_source`, `hash_dedup`, `link_entities`).

> Phases 1–8 are Release N (graph default, agent fallback retained). Phase 9 is Release N+1 after validation. Frontend requires **no functional change** (status/timeline API stable).

---

## 8. Datalake portability note (RDB-pointer pattern)

v1 keeps `chunks.content` in Postgres (acceptance §4, user override). To allow a future move to FS/datalake **without rewriting `cognify`**:

- Migration `004` adds nullable `chunks.content_uri` only; content hash remains on `sources.content_hash`.
- Introduce a thin `ChunkContentResolver.get_text(chunk)`: returns `chunk.content` when `content_uri` is NULL (today's behavior), else reads the blob at `content_uri` (e.g. `DATA_DIR/chunks/<sha256[:2]>/<sha256>`). All readers (`MapChunkService`, `LinkingService` R-TEXT, `ProvenanceService`) go through the resolver — **never** read `chunk.content` directly.
- A later, isolated migration can offload large `content` to blobs, set `content_uri`, and null the column — cognify/linking code is untouched because it only calls the resolver.
- `embedding` stays in pgvector regardless (VDB pointer is just the `chunks.id`), matching the diagram's pg_vector/RDB/VDB split while honoring "chunks in DB" for v1.

This is the minimal seam that satisfies the spec's "document how chunk storage could migrate … without rewriting cognify logic."

---

## 9. Acceptance criteria (testable, mapped to spec §"Testable acceptance criteria")

| # | Criterion | Verification |
|---|-----------|--------------|
| AC1 | `add` + `cognify` are separate compiled subgraphs in a parent ingest graph; **no `IngestToolGatingMiddleware` on the critical path** when `INGEST_ORCHESTRATOR=graph` | `test_cognify_subgraph.py` inspects graph nodes; `factory` chain assertion; spec §1 |
| AC2 | Upload pdf/txt/md → job `completed` → entity wiki pages exist with cross-entity `[[wikilinks]]` where chunks share entities | `test_ingest_graph_end_to_end` + golden §6.4(5); spec §2 |
| AC3 | **Structural** golden: merged entity count exact; ≥1 cross-chunk `related` link; negative pair not merged (rigged embeddings) | `test_cross_chunk_golden.py`; Tier B eval for real semantic quality |
| AC4 | Full chunk text remains queryable from Postgres after ingest | integration query `SELECT content FROM chunks`; spec §4 |
| AC5 | `pytest tests/ -v` green with `TEST_DATABASE_URL`→`munger_test` | CI; spec §5 |
| AC6 | `ingest_events` timeline includes `register_source`, `hash_dedup`, `link_entities` with correct `step_index`/`step_total` | integration test + `Ingest.tsx` labels; spec §6 |
| AC7 (new) | `entities.embedding` is populated for ingested sources; `ix_entities_embedding_hnsw` exists | DB assertion |
| AC8 (new) | `entity_relationships` rows carry `confidence` + `method` for cross-chunk links | golden assertion |

---

## 10. Risks + mitigations

| # | Risk | Likelihood/Impact | Mitigation |
|---|------|-------------------|-----------|
| R1 | Observability regression — moving emission from agent stream (`ingest_runner.py:120`) to nodes drops `agent_message`/`tool_call`/heartbeat events | M/H | Wrap every node in existing `pipeline_step`; pass `job_id` for `touch_job_heartbeat` (as `map_chunks` does, `map_chunk_service.py:265`); AC6 + heartbeat assertion |
| R2 | Checkpointer/resume semantics differ for `StateGraph` vs agent (`thread_id`, `recursion_limit`) | M/M | Keep Postgres checkpointer (`get_async_checkpointer`); per-job `thread_id` retained; integration test for mid-graph failure→resume |
| R3 | Over-merging entities (false positives) harms wiki quality | M/H | Type-gate; conservative `auto_merge=0.92`; LLM adjudication only in gray zone; negative golden fixture (System 1/2) as precision guard |
| R4 | Under-linking (false negatives) — pain persists | M/M | Three-leg hybrid incl. text-mention + cross-lingual aliases; tunables exposed; golden recall fixture |
| R5 | Deterministic embedding test diverges from real model behavior | L/M | `ScriptedLLMService` only for CI thresholds; document that real-model tuning is a separate (non-CI) eval; thresholds in `expected.json` |
| R6 | Scope creep into `/api/v2`, datalake, dir-walk | M/M | Explicit non-goals; v2 deferred ADR; portability is columns-only seam (§8) |
| R7 | Docs already stale (5-tool) compound confusion for executor | H/M | Phase 9 doc truth-up is in-scope and gated by AC; Planner flagged `ARCHITECTURE.md:154` + AGENTS.md |
| R8 | `pg_trgm`/hnsw-on-entities extension/index not present on Pigsty | L/H | `004` `CREATE EXTENSION IF NOT EXISTS` + `_require_pgvector()`-style guard; bootstrap script note |
| R9 | LangGraph `Send` fan-out increases checkpoint volume per chunk | M/M | `INGEST_MAP_MODE` flag; concurrency cap on Send dispatch; monitor checkpoint row growth; fallback to service gather |

---

## ADR: Cognee-inspired ingest subgraph refactor

| Field | Decision |
|-------|----------|
| **Decision** | Replace agent+gating with LangGraph `add` + `cognify` subgraphs; add `LinkingService` for within-source cross-chunk merge/relate; keep Postgres RDB+pgvector; chunks in DB |
| **Drivers** | Extensibility (4-edit coupling today); cross-chunk linking quality (exact dedup insufficient); diagram/spec mandate |
| **Alternatives considered** | A2 keep agent+gating (rejected — spec); plain async pipeline no graph (rejected — LangGraph constraint); semantic-only / fuzzy-only linking (rejected alone); global fuzzy merge (deferred — blast radius) |
| **Why chosen** | Services already implement map/reduce; graph gives explicit staged contract; hybrid linking addresses user's core pain; within-source scope is brownfield-safe |
| **Consequences** | Must re-home observability to node wrappers; 3 new timeline steps; `entities.embedding` finally populated; upload dedup (409) vs worker re-ingest dedup are separate layers |
| **Follow-ups** | Global semantic linking; `improve` pass (Tavily); optional `content_uri` blob offload; `entity_graph_edges` materialized view for Graph UI; `/api/v2` if shape changes |

## Resolved open questions

| # | Resolution |
|---|------------|
| 1 | **LangGraph `Send` map-reduce** for per-chunk parallel (`fanout_chunks` + `chunk_map_subgraph`); `map_single_chunk` extracted from `MapChunkService` |
| 6 | **No GDB** — graph = `entity_relationships` + `entity_mentions`; optional materialized view for read queries |
| 7 | **Unified Postgres** — pgvector + RDB same instance; chunk text + metadata in `chunks` table, not FS/Lake |
| 2 | LLM adjudication in gray zone: **on by default**, disable via `INGEST_LINK_LLM_ADJUDICATE=false` for deterministic CI |
| 3 | Merge winner: highest within-source `mention_count`, tie → lowest id |
| 4 | **Within-source only** for fuzzy/semantic merge; global exact-name merge stays in `reduce` |
| 5 | `/api/v2` deferred; v1 ingest API unchanged |

## Execution handoff

### Available agent roster

| Agent | Lane |
|-------|------|
| `executor` | subgraph nodes, services |
| `test-engineer` | golden corpus, ScriptedLLM, integration |
| `code-reviewer` | post-phase review |
| `verifier` | acceptance criteria check |
| `debugger` | resume/idempotency failures |

### `$ralph` staffing (sequential)

1. **Schema + graph scaffold** — executor (medium)
2. **add subgraph** — executor (medium)
3. **cognify reuse path** — executor (medium)
4. **LinkingService** — executor (high) ← critical path
5. **IngestRunner switch + tests** — test-engineer + executor (high)
6. **Docs + deprecate** — executor (low)

Suggested: `$ralph .omx/plans/ralplan-cognee-inspired-pipeline-refactor.md`

### `$team` staffing (parallel)

| Lane | Owner | Scope |
|------|-------|-------|
| A | executor | `app/runtime/graphs/` + IngestRunner |
| B | executor | `linking_service.py` + migration 004 |
| C | test-engineer | ScriptedLLM + golden + resume tests |
| D | executor | `pipeline_events` step registry + `Ingest.tsx` |

Launch: `$team .omx/plans/ralplan-cognee-inspired-pipeline-refactor.md`

**Team verification path:** Lanes A+B+C produce green `pytest tests/unit tests/integration -v`; Lane D confirms timeline renders 11 steps; verifier runs AC1–AC8 checklist.

**Ralph verification after team:** full `pytest tests/ -v`, manual ingest of `munger_circle.txt` fixture, confirm wikilinks in UI.

## Changelog (v1 → v2 consensus)

- C1: Reuse `sources.content_hash`; remove redundant sha fields
- K1: Document upload 409 vs worker `n_hash_dedup` roles
- C2: Add `register_source`, `hash_dedup`, `link_entities` to step registry + frontend
- C3: Within-source candidate universe only
- C4/K2: Mention uniqueness, merge guards, delete-first idempotency
- C5: Split CI structural golden vs non-CI eval harness
- K3: Resume + agent-fallback tests added
- C6: Remove singular `graph/`/`nodes/` placeholders
- v2.1: `n_wiki` dual pipeline_step; `n_skip` contract; mention collapse before unique index; Tier A disables LLM adjudication
- v2.2: LangGraph Send map-reduce (Medium ref); references-as-graph (no GDB); unified Postgres storage ADR (chunks in RDB not FS)
