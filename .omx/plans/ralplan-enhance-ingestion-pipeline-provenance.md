# RALPLAN: Provenance-First Ingestion Pipeline Enhancement

**Slug:** `enhance-ingestion-pipeline-provenance`  
**Spec:** `.omc/specs/deep-dive-enhance-ingestion-pipeline-provenance.md`  
**Observability spec:** `.omx/specs/deep-interview-ingest-pipeline-observability.md` (merged Phase 4b)  
**Type:** Brownfield (5-tool v1 → 9+1 provenance-first pipeline)  
**Mode:** Consensus (RALPLAN-DR + ADR)  
**Date:** 2026-06-08  
**Status:** APPROVED v2 — Architect CONCERNS + Critic ITERATE addressed

### Consensus Amendments (v2)

| Issue | Resolution |
|-------|------------|
| Skill-parameterized gating | `IngestToolGatingMiddleware(tool_order, allowed_tools, aliases)` constructed per-skill in `make_ingest_lead_agent(skill_name)` |
| Char-offset coordinate system | **Document-global** offsets on `EntityMention`; excerpt = `content_text[char_start:char_end]`; `chunks` store `doc_char_start`/`doc_char_end` |
| CREATE EXTENSION permission | Extension created **only** in admin bootstrap scripts; Alembic `003` assumes extension exists (guard + clear error) |
| Embedding dimension | **768** canonical (`nomic-embed-text`); `embedding_dimensions` config drives `vector(N)`; runtime validates `len(embed)`; spec 1536 example is non-canonical |
| entity_relationships idempotency | `UNIQUE (source_entity_id, target_entity_id, relationship_type, source_id)` + `ON CONFLICT DO UPDATE` |
| Wiki incremental | Update via `entity.wiki_page_id` → `update_page`; append chunk citations to frontmatter; re-ingest deletes source-scoped mentions/relationships first |
| Instructor async | `instructor.from_openai(AsyncOpenAI(...))` with async extraction methods; no sync bridge |
| Long ingest stale jobs | `job_stale_minutes` → **45**; heartbeat updates inside `ChunkService` prefix loop |
| Hybrid FTS | Add `wiki_pages.search_vector tsvector` + GIN in `003`; hybrid = tsvector + pgvector RRF |
| Tool alias gating | `_completed_tools` normalizes aliases (`extract_source_text` → `parse_document`) |

---

## Executive Summary

Replace Munger's monolithic 5-tool ingest pipeline with a **provenance-first, chunk-indexed pipeline** while preserving the DeerFlow harness (vanilla LangGraph agent + SKILL.md + fine-grained tools). Deliver all 9 ingest tools, pgvector semantic search, Instructor per-chunk extraction + gleaning, LightRAG-style incremental entity/relationship/wiki updates, four DeerFlow skills, and a backfill path for existing sources — in **one release**.

**Current state (evidence):**

| Area | Location | Gap |
|------|----------|-----|
| 5 monolithic tools | `munger/backend/app/runtime/tools/ingest_tools.py` | No chunk/provenance tools |
| No chunk models | `munger/backend/app/models/` | No `Chunk`, `ChunkExtraction`, `EntityRelationship` |
| EntityMention | `munger/backend/app/models/entity.py` | `source_id` + 200-char `context` only |
| Semantic search stub | `munger/backend/app/services/search_service.py:233-260` | ILIKE fallback, no stored vectors |
| Alembic head | `munger/backend/alembic/versions/002_drop_workflow_tables.py` | No pgvector, no provenance DDL |
| Active skill | `munger/backend/data/workflows/default-ingest/SKILL.md` | 5-tool legacy order |

---

## RALPLAN-DR Summary

### Principles

1. **Harness preservation** — Keep vanilla LangGraph agent + SKILL.md + `IngestToolGatingMiddleware`; tools call services, not external GraphRAG/LlamaIndex CLIs.
2. **Provenance as data model** — Every new `EntityMention` must link `entity → chunk → source` with `char_start`/`char_end`; wiki pages cite chunk excerpts.
3. **Postgres sufficiency** — Single Pigsty Postgres for relational, pgvector, and graph edges; no Neo4j or separate vector DB.
4. **Incremental merge** — LightRAG pattern: upsert entities/relationships/wiki per source; no full graph rebuild.
5. **Brownfield migration** — Backfill existing `content_text` in-place; nullable `chunk_id` during transition; no wipe required.

### Decision Drivers (Top 3)

1. **Provenance bar** — User chose chunk-level citations in wiki (not entity-name grep); drives schema, tool split, and wiki generation.
2. **Single-release scope** — Full 9 tools + pgvector + sub-skills in one spec; no phased MVP deferral.
3. **Pigsty + int PK conventions** — Must work on existing Postgres deployment with `int` FKs (`sources.id`, `entities.id`); adapt ideas-doc UUIDs to Munger ORM.

### Viable Options

#### Option A: Full spec in one release (chosen)

Split `ingest_tools.py` into 9+1 modules, add `003_*` migration, wire pgvector search, migrate all four skills, add backfill endpoint.

| Pros | Cons |
|------|------|
| Matches user interview (full pipeline, backfill) | Large PR surface; ingest tests break until harness slice lands |
| Avoids intermediate broken states (5-tool + chunks table unused) | Long-running ingests risk stale job timeout |
| Delivers provenance + retrieval together | Requires pgvector validated on Pigsty before merge |

#### Option B: Schema + chunking first, extraction second release

Phase 1: `chunks` table + `chunk_document` + backfill chunks only. Phase 2: Instructor extraction, resolution, wiki citations.

| Pros | Cons |
|------|------|
| Smaller initial PR; validates pgvector early | Violates user "full pipeline in one spec" decision |
| Ingest still works with old entity extraction | `EntityMention` provenance incomplete until phase 2 |
| Lower CI blast radius | Two migrations, two skill rewrites, operator confusion |

**Invalidation rationale:** User explicitly chose full 9-tool pipeline in one release (interview Round 1). Option B deferred.

#### Option C: Keep 5 tools, add provenance inside monoliths

Extend existing tools internally (chunk inside `extract_entities_from_text`) without harness/skill changes.

| Pros | Cons |
|------|------|
| Minimal harness/test churn | Violates spec tool decomposition and gating transparency |
| Faster short-term | No sub-skill routing (`entity-extract-only`, `wiki-regenerate`) |
| | Instructor gleaning/resolution not independently callable |

**Invalidation rationale:** Spec requires 9 named tools, skill `allowed-tools`, and sub-skill routing; monolith approach blocks incremental wiki/regenerate flows.

---

## ADR: Provenance-First 9-Tool Pipeline on Postgres + pgvector

### Decision

Implement **Option A**: full provenance-first pipeline in one release — Alembic `003_*` schema, 9+1 ingest tools in dedicated modules, pgvector on `chunks.embedding`, Instructor per-chunk extraction + gleaning, LightRAG incremental merge, four DeerFlow skills, `POST /api/sources/{id}/backfill`, and semantic/hybrid search with chunk attribution.

**Planner defaults** (resolve analyst ambiguities; override via `adjust`):

| Topic | Default |
|-------|---------|
| Embedding dimension | **768** (`vector(768)`) aligned with default `nomic-embed-text` in `app/core/config.py:38`; add `embedding_dimensions` setting |
| Tool args | **`source_id` required**; optional params (`chunk_size`, `max_concurrency`, `max_gleanings`) with defaults in tool impl, not in agent schema (preserve `SourceIdArgs` for harness tests) |
| Tool order | `parse_document` → `chunk_document` → `extract_entities_from_chunks` → `glean_entities` → `resolve_entities` → `summarize_source` → `generate_wiki_pages` → `link_wiki_pages` → `finalize_ingest` |
| Wiki citations | YAML frontmatter `sources: [{chunk_id, char_start, char_end, excerpt}]` + blockquote excerpt in body |
| `entity_relationships` | Dedicated table (per spec SQL), not JSONB on `entities` |
| Backfill | Skip `parse_document` if `content_text` present; delete stale `chunks`/`chunk_extractions`/`entity_mentions` for source; run chunk→extract→glean→resolve→wiki; optional re-summarize |
| Deprecation | Keep `extract_source_text` and `create_wiki_pages` as **aliases** one release; gating fatal check uses `parse_document` |
| Quality metric | Log `entities_per_chunk` in `finalize_ingest` + `ingest_events`; warn if outside 3–15, do not fail |
| `max_agent_steps` | Raise default to **30** in `app/core/config.py` for 9-step pipeline headroom |

### Drivers

- Interview: full pipeline, backfill, chunk-level wiki citations
- Existing harness is reusable; missing layer is schema + tool granularity + retrieval
- Postgres + pgvector sufficient per spec and trace

### Alternatives Considered

- **Option B (phased)** — rejected (user scope)
- **Option C (monolith)** — rejected (harness/sub-skill requirements)
- **Neo4j / Pinecone** — rejected (spec non-goals)
- **UUID chunk PKs** — rejected (Munger int PK convention)

### Consequences

- **Positive:** Queryable provenance chain; real semantic search; sub-skills for partial re-runs; incremental wiki/relationship merge
- **Negative:** Large coordinated change across models, tools, skills, tests; backfill may change entity counts and wiki content; contextual prefix adds LLM cost/latency per chunk
- **Neutral:** Frontend provenance UI deferred (non-goal); API schema extensions only where needed

### Follow-ups

- Phase 3 (later): GraphRAG community detection / Leiden clustering (`graspologic` deferred)
- Frontend: chunk citation display, provenance drill-down
- Automatic re-ingest on embedding model change (manual via `entity-extract-only` for now)
- IVFFlat/HNSW index tuning once chunk volume justifies it

---

## Implementation Phases (Ordered Dependencies)

### Phase 1: Infrastructure & Schema Foundation

**Goal:** pgvector available; provenance tables exist; ORM + API schemas registered.

**Tasks:**

1. **Dependencies** — Add to `munger/backend/requirements.txt`:
   - `instructor>=1.0`
   - `tiktoken>=0.7`
   - `pgvector>=0.3`

2. **Postgres bootstrap** — Extend:
   - `munger/backend/scripts/bootstrap_postgres.py` — `CREATE EXTENSION IF NOT EXISTS vector` on `munger` DB (superuser/admin path)
   - `munger/backend/scripts/bootstrap_test_postgres.py` — same for `munger_test`
   - Document Pigsty pre-req in `munger/backend/AGENTS.md`

3. **Config** — Extend `munger/backend/app/core/config.py`:
   - `embedding_dimensions: int = 768`
   - `ingest_chunk_size_tokens: int = 600`
   - `ingest_chunk_overlap_tokens: int = 100`
   - `ingest_max_gleanings: int = 1`
   - `ingest_extract_concurrency: int = 5`
   - `max_agent_steps: int = 30`

4. **Alembic migration** — Create `munger/backend/alembic/versions/003_provenance_chunks_pgvector.py`:
   - **No `CREATE EXTENSION`** — assume admin bootstrap ran first; migration checks `pg_extension` and fails with actionable message if missing
   - `chunks` table (`source_id`, `chunk_index`, `content`, `contextual_prefix`, `token_count`, `doc_char_start`, `doc_char_end`, `embedding vector(768)`, `embedding_model`, timestamps, `UNIQUE(source_id, chunk_index)`)
   - `chunk_extractions` table (`chunk_id`, `source_id`, `entities` JSONB, `relationships` JSONB, `glean_round`, `UNIQUE(chunk_id, glean_round)`)
   - `entity_relationships` table with `UNIQUE (source_entity_id, target_entity_id, relationship_type, source_id)`
   - `ALTER entity_mentions ADD chunk_id, char_start, char_end` (nullable; **document-global** offsets)
   - `ALTER entities ADD embedding vector(768)` (nullable)
   - `ALTER wiki_pages ADD search_vector tsvector` + GIN index for hybrid FTS
   - HNSW index on `chunks.embedding` (`vector_cosine_ops`) — create after table, `IF NOT EXISTS`

5. **ORM models** — New files:
   - `munger/backend/app/models/chunk.py` — `Chunk`
   - `munger/backend/app/models/chunk_extraction.py` — `ChunkExtraction`
   - `munger/backend/app/models/entity_relationship.py` — `EntityRelationship`
   - Extend `munger/backend/app/models/entity.py` — `EntityMention.chunk_id`, `char_start`, `char_end`; `Entity.embedding`
   - Register in `munger/backend/app/models/__init__.py`

6. **API schemas** — Extend:
   - `munger/backend/app/schemas/entity.py` — `EntityMentionResponse` adds `chunk_id`, `char_start`, `char_end`
   - `munger/backend/app/schemas/search.py` — `SearchResult` adds `chunk_id`, `source_id`, `char_start`, `char_end`, `excerpt`
   - New `munger/backend/app/schemas/chunk.py` — `ChunkResponse`, `ProvenanceChainItem`

**Acceptance criteria:**

- [ ] `alembic upgrade head` succeeds on fresh `munger_test` after bootstrap
- [ ] `SELECT extname FROM pg_extension WHERE extname = 'vector'` returns row
- [ ] SQLAlchemy can insert/query `Chunk` with `embedding` column
- [ ] `EntityMention.chunk_id` nullable; existing rows unaffected

---

### Phase 2: Service Layer (Chunking, Extraction, Resolution, Relationships)

**Goal:** Business logic for provenance pipeline; tools remain thin wrappers.

**Tasks:**

1. **Chunking service** — `munger/backend/app/services/chunk_service.py`:
   - Tiktoken split (`chunk_size=600`, `overlap=100`; single chunk if doc <1200 tokens)
   - Store `doc_char_start`/`doc_char_end` on each chunk (document-global bounds)
   - `EntityMention.char_start`/`char_end` are **document-global** (same coordinate system as `content_text`)
   - Anthropic contextual prefix: sequential LLM calls per chunk (prompt caching on full doc); on failure: log warning, embed raw chunk
   - Persist chunks; call `LLMService.embed_texts()` on `contextual_prefix + "\n\n" + content`
   - Idempotent: delete existing chunks for `source_id` before re-chunk

2. **Instructor schemas** — `munger/backend/app/runtime/tools/schemas/`:
   - `entity.py` — `ExtractedEntity`, `ExtractedRelationship`, `ExtractionResult`, `GleanResult`
   - `chunk.py` — `ChunkMetadata`

3. **Extraction service** — `munger/backend/app/services/extraction_service.py`:
   - Instructor async client: `instructor.from_openai(AsyncOpenAI(...))` sharing `LLMService` base URL/key
   - `extract_entities_from_chunks(source_id, max_concurrency=5)` — per-chunk structured extraction → `chunk_extractions` (`glean_round=0`)
   - `glean_entities(source_id, max_gleanings=1)` — GraphRAG-style CONTINUE/LOOP prompts → append `glean_round=1`

4. **Resolution service** — `munger/backend/app/services/resolution_service.py`:
   - Canonicalize names; embedding cosine block against `entities.embedding`; LLM confirm on ambiguous pairs
   - Upsert `entities` + `entity_mentions` with `chunk_id`, `char_start`, `char_end`
   - Delete prior `entity_mentions` for `source_id` before writing new provenance
   - Merge `entity_relationships` from `chunk_extractions.relationships` (upsert by `source_entity_id + target_entity_id + relationship_type + source_id`)

5. **Extend existing services:**
   - `munger/backend/app/services/entity_service.py` — delegate to resolution/extraction; keep `find_or_create` for backward compat
   - `munger/backend/app/services/llm_service.py` — ensure `embed_texts` returns correct dimension; gate zero-vector providers with explicit error for chunk embed
   - `munger/backend/app/services/storage_service.py` — no change to extract; `parse_document` wraps `extract_text`

6. **Provenance query** — `munger/backend/app/services/provenance_service.py`:
   - `get_provenance_chain(entity_id)` → `[{source_id, chunk_id, char_start, char_end, excerpt}]`

**Acceptance criteria:**

- [ ] Unit tests: tiktoken chunk boundaries + char offsets match `content_text`
- [ ] Unit tests: Instructor schema round-trip with mocked LLM
- [ ] Unit tests: resolution writes mentions with non-null `chunk_id`
- [ ] Unit tests: relationship merge is idempotent on re-run

---

### Phase 3: Tool Decomposition (9 + 1)

**Goal:** Replace monolithic `ingest_tools.py` with spec tool layout; maintain `build_ingest_tools()` entrypoint.

**New modules under `munger/backend/app/runtime/tools/`:**

| Module | Tools | Wraps |
|--------|-------|-------|
| `parsing.py` | `parse_document` | `StorageService.extract_text` + status `extracting` |
| `chunking.py` | `chunk_document` | `ChunkService.chunk_and_embed` + status `chunking` |
| `extraction.py` | `extract_entities_from_chunks`, `glean_entities` | `ExtractionService` |
| `resolution.py` | `resolve_entities` | `ResolutionService` |
| `summarization.py` | `summarize_source` | existing summarize logic (from `ingest_tools.py`) |
| `wiki_generation.py` | `generate_wiki_pages`, `link_wiki_pages` | `WikiService` + chunk excerpts |
| `finalization.py` | `finalize_ingest` | `WikiService.update_index`, quality metrics |
| `munger_analysis.py` | `analyze_source_12d` | thin wrapper → `munger_service.py` |

**Refactor `ingest_tools.py`:**

- Export `INGEST_TOOL_ORDER` (9 steps) as single source of truth
- `build_ingest_tools()` aggregates all modules
- Deprecation aliases: `extract_source_text` → calls `parse_document`; `create_wiki_pages` → calls `generate_wiki_pages` + `link_wiki_pages` (or split alias mapping)
- `extract_entities_from_text` alias → `extract_entities_from_chunks` (log deprecation)

**Wiki generation changes (`wiki_generation.py`):**

- `generate_wiki_pages`: incremental — touch entities from current source extractions only
- Cite chunks: frontmatter YAML + `> excerpt` blockquote from `content_text[mention.char_start:mention.char_end]`
- Update existing wiki: if `entity.wiki_page_id` set → `update_page`; else `create_page`
- `link_wiki_pages`: parse `[[wikilinks]]`; enrich from `entity_relationships` where `link_type` maps to `related`/`see_also`

**Acceptance criteria:**

- [ ] `build_ingest_tools()` returns 9 core tools (+ aliases + `analyze_source_12d`)
- [ ] Each tool updates `Source.status` appropriately
- [ ] `finalize_ingest` logs `entities_per_chunk` ratio; warns outside 3–15
- [ ] New ingest produces `EntityMention` rows with non-null `chunk_id`

---

### Phase 4: Harness, Skills & Job Routing

**Goal:** Agent executes 9-step order; sub-skills routable by job type.

**Tasks:**

1. **Gating middleware** — `munger/backend/app/runtime/harness/middlewares/ingest_tool_gating_middleware.py`:
   - Constructor: `IngestToolGatingMiddleware(tool_order, allowed_tools, aliases={...})`
   - `next_allowed_tool()` iterates `tool_order` intersected with `allowed_tools`
   - `_completed_tools` normalizes alias names (`extract_source_text` → `parse_document`)
   - `_fatal_extract` → `parse_document` (accept alias during transition)
   - `make_ingest_lead_agent(skill_name)` passes skill's `tool_order` or default `INGEST_TOOL_ORDER`

2. **Skill types** — `munger/backend/app/runtime/harness/skills/types.py`:
   - Add `tool_order: list[str] | None`

3. **Skill loader** — `munger/backend/app/runtime/harness/skills/loader.py`:
   - Parse `tool-order` YAML frontmatter field

4. **Skills rewrite** — `munger/backend/data/workflows/`:
   - `default-ingest/SKILL.md` — 9-tool order, quality metrics, `allowed-tools`
   - `entity-extract-only/SKILL.md` — DeerFlow format; tools: `parse_document`, `chunk_document`, `extract_entities_from_chunks`, `glean_entities`, `resolve_entities`
   - `wiki-regenerate/SKILL.md` — **new**; tools: `generate_wiki_pages`, `link_wiki_pages`
   - `munger-12-dimension/SKILL.md` — DeerFlow format; `analyze_source_12d` only

5. **Agent prompt** — `munger/backend/app/runtime/agents/ingest_prompt.py`:
   - Update 9-step sequence and fatal-parse rule

6. **Job routing:**
   - `munger/backend/app/models/ingest_job.py` — add `skill_name: str = "ingest"` column (migration in `003` or `004` if split)
   - `munger/backend/app/runtime/agents/ingest_lead_agent.py` — `make_ingest_lead_agent(skill_name: str = "ingest")`
   - `munger/backend/app/runtime/ingest_runner.py` — pass `job.skill_name`
   - `munger/backend/app/api/sources.py` — `POST /ingest` accepts optional `?skill=ingest|entity-extract-only|wiki-regenerate`
   - `munger/backend/app/services/ingest_job_service.py` — persist `skill_name`

7. **Docs** — Update `munger/backend/WORKFLOW_ARCH.md`, `munger/backend/AGENTS.md` tool lists

**Acceptance criteria:**

- [ ] Default ingest runs 9 tools in order; gating blocks out-of-order calls
- [ ] `entity-extract-only` job runs 5-tool subset without wiki steps
- [ ] `wiki-regenerate` runs wiki tools only
- [ ] `test_ingest_agent.py` and `test_ingest_tool_gating.py` pass with new order

---

### Phase 4b: Pipeline Observability (operator UI)

**Goal:** Operator-friendly ingest visibility on Ingest page — extend existing `ingest_events`, no external APM in v1.  
**Spec:** `.omx/specs/deep-interview-ingest-pipeline-observability.md`

**Tasks:**

1. **Pipeline events helper** — `munger/backend/app/runtime/pipeline_events.py`:
   - `emit_pipeline_step_start(source_id, job_id, step_key, step_index, step_total, label)`
   - `emit_pipeline_step_complete(..., duration_ms, metrics: dict)`
   - `emit_pipeline_step_failed(..., message)`
   - `emit_pipeline_summary(...)` — entities_per_chunk, counts
   - Payload includes OTel-ready optional fields (`trace_id`, `span_id`, `duration_ms`) — no exporter

2. **Wire into tools** — each tool module (Phase 3) emits start/complete/failed with step-specific metrics:
   - `chunk_document` → `chunk_count`, `total_tokens`
   - `extract_entities_from_chunks` → `entities_raw`, `chunks_processed`
   - `glean_entities` → `entities_added`
   - `resolve_entities` → `mentions_created`, `dedup_rate`
   - `generate_wiki_pages` / `link_wiki_pages` → page/link counts

3. **Status API** — `munger/backend/app/api/sources.py`:
   - Add `current_step` (`key`, `label`, `index`, `total`) and `step_metrics` to `GET /{source_id}/status`
   - Derive from latest `pipeline_step_*` events or denormalize on `IngestJob`

4. **Frontend** — `app/src/pages/Ingest.tsx`:
   - Primary timeline: human step cards (N/9 progress), not raw `tool_call` / `agent_message`
   - Show per-step metrics on completion; readable error on `pipeline_step_failed`
   - Update `IN_FLIGHT_STATUSES` for new statuses (`chunking`, etc.)
   - Keep 2s polling (no SSE/WebSocket)

5. **Tests** — `munger/backend/tests/unit/test_pipeline_events.py`:
   - Event emission per tool; status API `current_step` derivation

**Non-goals (v1):** LLM token/cost tracking; LangSmith/Prometheus/OTel exporter; cross-run dashboard.

**Acceptance criteria:**

- [ ] Each 9-tool step emits `pipeline_step_start` + `pipeline_step_complete` (or `failed`)
- [ ] `GET /status` returns `current_step` + `step_metrics` for in-flight jobs
- [ ] Ingest page shows operator labels without reading snake_case tool names
- [ ] `finalize_ingest` emits `pipeline_summary` with quality ratios

---

### Phase 5: Retrieval API & Hybrid Search

**Goal:** Semantic search queries `chunks.embedding`; API returns provenance attribution.

**Tasks:**

1. **Search service** — `munger/backend/app/services/search_service.py`:
   - `semantic_search`: pgvector cosine (`embedding <=> query_vec`) on `chunks`
   - Return `chunk_id`, `source_id`, excerpt, score
   - `hybrid_search` (new): RRF fusion of chunk vectors + wiki FTS (`to_tsvector` on `wiki_pages.content` if not present, add `search_vector` column in `003` or lightweight ILIKE fallback initially)
   - Provider gate: require non-zero embedding for semantic path

2. **Search API** — `munger/backend/app/api/search.py`:
   - Wire `/api/search/semantic` to real pgvector query
   - Add `/api/search/hybrid` (optional query param on existing search)

3. **Provenance API** — `munger/backend/app/api/entities.py`:
   - Extend `GET /api/entities/{id}/mentions` with chunk fields
   - Add `GET /api/entities/{id}/provenance` → provenance chain

4. **Frontend types** (minimal) — `app/src/` only if existing API client types break:
   - Entity mention / search result types if referenced

**Acceptance criteria:**

- [ ] `GET /api/search/semantic?q=...` returns results with `chunk_id` and `source_id`
- [ ] `GET /api/entities/{id}/provenance` returns source→chunk→excerpt chain
- [ ] Hybrid search returns both chunk and wiki hits

---

### Phase 6: Backfill, Integration Tests & Verification

**Goal:** Existing sources gain provenance; CI green; manual probe documented.

**Tasks:**

1. **Backfill endpoint** — `munger/backend/app/api/sources.py`:
   - `POST /api/sources/{id}/backfill` — enqueues job with `skill_name=entity-extract-only` extended pipeline or dedicated backfill runner
   - Behavior: skip parse if `content_text`; wipe chunks/extractions/mentions for source; run chunk→extract→glean→resolve→summarize→wiki→link→finalize
   - Return 202 + `job_id` (same as ingest)

2. **CLI (optional)** — `munger/backend/scripts/backfill_source.py` — operator one-off

3. **Tests** — `munger/backend/tests/`:
   - `unit/test_chunk_service.py` — tiktoken, offsets, idempotent delete
   - `unit/test_extraction_schemas.py` — Pydantic/Instructor models
   - `unit/test_provenance_chain.py` — mention→chunk→source join
   - `unit/test_semantic_search.py` — pgvector query with fixture embeddings
   - Update `unit/test_ingest_agent.py` — 9 tool names, skill loads
   - Update `unit/test_ingest_tool_gating.py` — new order, fatal `parse_document`
   - Update `unit/test_llm_adapter.py` — tool name if needed
   - Update `integration/test_provider_gate.py` — assert `chunk_id IS NOT NULL` on mentions
   - Replace placeholder in `integration/test_postgres_worker.py` — job claims and completes (mock LLM)

4. **Docker** — `munger/backend/Dockerfile` — pip install new deps

**Acceptance criteria:**

- [ ] `pytest tests/ -v` passes in `munger/backend/`
- [ ] `npm run build` passes in `app/` (if types touched)
- [ ] Manual: ingest >10k char PDF → mentions have `chunk_id` → wiki contains blockquote citation
- [ ] Backfill on v1 source produces chunks without re-upload

---

## File-Level Touch List

### Migrations & Bootstrap

| File | Action |
|------|--------|
| `munger/backend/alembic/versions/003_provenance_chunks_pgvector.py` | **Create** |
| `munger/backend/scripts/bootstrap_postgres.py` | **Edit** — `CREATE EXTENSION vector` |
| `munger/backend/scripts/bootstrap_test_postgres.py` | **Edit** — same |
| `munger/backend/requirements.txt` | **Edit** — instructor, tiktoken, pgvector |
| `munger/backend/Dockerfile` | **Edit** — deps |

### Models & Schemas

| File | Action |
|------|--------|
| `munger/backend/app/models/chunk.py` | **Create** |
| `munger/backend/app/models/chunk_extraction.py` | **Create** |
| `munger/backend/app/models/entity_relationship.py` | **Create** |
| `munger/backend/app/models/entity.py` | **Edit** — provenance + embedding |
| `munger/backend/app/models/ingest_job.py` | **Edit** — `skill_name` |
| `munger/backend/app/models/__init__.py` | **Edit** — exports |
| `munger/backend/app/schemas/entity.py` | **Edit** — mention fields |
| `munger/backend/app/schemas/search.py` | **Edit** — chunk attribution |
| `munger/backend/app/schemas/chunk.py` | **Create** |

### Services

| File | Action |
|------|--------|
| `munger/backend/app/services/chunk_service.py` | **Create** |
| `munger/backend/app/services/extraction_service.py` | **Create** |
| `munger/backend/app/services/resolution_service.py` | **Create** |
| `munger/backend/app/services/provenance_service.py` | **Create** |
| `munger/backend/app/services/entity_service.py` | **Edit** — delegate |
| `munger/backend/app/services/search_service.py` | **Edit** — pgvector + hybrid |
| `munger/backend/app/services/llm_service.py` | **Edit** — dimension guard |
| `munger/backend/app/services/ingest_job_service.py` | **Edit** — skill_name |
| `munger/backend/app/services/wiki_service.py` | **Edit** — incremental + citations |

### Tools & Harness

| File | Action |
|------|--------|
| `munger/backend/app/runtime/tools/ingest_tools.py` | **Edit** — aggregator + order |
| `munger/backend/app/runtime/tools/parsing.py` | **Create** |
| `munger/backend/app/runtime/tools/chunking.py` | **Create** |
| `munger/backend/app/runtime/tools/extraction.py` | **Create** |
| `munger/backend/app/runtime/tools/resolution.py` | **Create** |
| `munger/backend/app/runtime/tools/summarization.py` | **Create** |
| `munger/backend/app/runtime/tools/wiki_generation.py` | **Create** |
| `munger/backend/app/runtime/tools/finalization.py` | **Create** |
| `munger/backend/app/runtime/tools/munger_analysis.py` | **Create** |
| `munger/backend/app/runtime/tools/schemas/entity.py` | **Create** |
| `munger/backend/app/runtime/tools/schemas/chunk.py` | **Create** |
| `munger/backend/app/runtime/tools/__init__.py` | **Edit** |
| `munger/backend/app/runtime/harness/middlewares/ingest_tool_gating_middleware.py` | **Edit** |
| `munger/backend/app/runtime/harness/skills/types.py` | **Edit** |
| `munger/backend/app/runtime/harness/skills/loader.py` | **Edit** |
| `munger/backend/app/runtime/agents/ingest_lead_agent.py` | **Edit** |
| `munger/backend/app/runtime/agents/ingest_prompt.py` | **Edit** |
| `munger/backend/app/runtime/ingest_runner.py` | **Edit** |

### Skills

| File | Action |
|------|--------|
| `munger/backend/data/workflows/default-ingest/SKILL.md` | **Rewrite** |
| `munger/backend/data/workflows/entity-extract-only/SKILL.md` | **Rewrite** |
| `munger/backend/data/workflows/wiki-regenerate/SKILL.md` | **Create** |
| `munger/backend/data/workflows/munger-12-dimension/SKILL.md` | **Rewrite** |

### API

| File | Action |
|------|--------|
| `munger/backend/app/api/sources.py` | **Edit** — skill param, backfill |
| `munger/backend/app/api/search.py` | **Edit** — semantic/hybrid |
| `munger/backend/app/api/entities.py` | **Edit** — provenance |
| `munger/backend/app/core/config.py` | **Edit** — new settings |

### Tests

| File | Action |
|------|--------|
| `munger/backend/tests/unit/test_ingest_agent.py` | **Edit** |
| `munger/backend/tests/unit/test_ingest_tool_gating.py` | **Edit** |
| `munger/backend/tests/unit/test_llm_adapter.py` | **Edit** |
| `munger/backend/tests/unit/test_chunk_service.py` | **Create** |
| `munger/backend/tests/unit/test_extraction_schemas.py` | **Create** |
| `munger/backend/tests/unit/test_provenance_chain.py` | **Create** |
| `munger/backend/tests/unit/test_semantic_search.py` | **Create** |
| `munger/backend/tests/integration/test_provider_gate.py` | **Edit** |
| `munger/backend/tests/integration/test_postgres_worker.py` | **Edit** |

### Docs

| File | Action |
|------|--------|
| `munger/backend/WORKFLOW_ARCH.md` | **Edit** |
| `munger/backend/AGENTS.md` | **Edit** |
| `ARCHITECTURE.md` | **Edit** — ingest/provenance section (optional) |

### Frontend (minimal)

| File | Action |
|------|--------|
| `app/src/**` (API types only if broken) | **Edit** — conditional |

---

## Verification Steps

### Automated

```bash
# 1. Bootstrap test DB with pgvector
cd munger/backend
export TEST_DATABASE_URL=postgresql+psycopg://munger_app:PASSWORD@localhost:5432/munger_test
python scripts/bootstrap_test_postgres.py

# 2. Verify extension
psql $TEST_DATABASE_URL -c "SELECT extname FROM pg_extension WHERE extname = 'vector';"

# 3. Migrate
alembic upgrade head

# 4. Backend tests
pytest tests/ -v

# 5. Frontend (if API types changed)
cd ../../app && npm run build && npm run lint
```

### Manual Probes

1. **pgvector on Pigsty (pre-flight):**
   ```sql
   CREATE EXTENSION IF NOT EXISTS vector;
   SELECT '[1,2,3]'::vector;
   ```

2. **Full ingest (PDF >10k chars):**
   - `POST /api/sources/upload` → `POST /api/sources/{id}/ingest`
   - Poll `GET /api/sources/{id}/status` until `completed`
   - `GET /api/entities/{id}/mentions` → `chunk_id`, `char_start`, `char_end` populated
   - `GET /api/entities/{id}/provenance` → excerpt chain
   - Wiki page content contains blockquote citation; frontmatter lists chunk refs

3. **Semantic search:**
   - `GET /api/search/semantic?q=<topic from doc>`
   - Results include `chunk_id`, `source_id`, relevant excerpt

4. **Backfill v1 source:**
   - Pick source ingested before migration (mentions without `chunk_id`)
   - `POST /api/sources/{id}/backfill`
   - After completion: chunks exist; mentions have `chunk_id`; wiki updated

5. **Sub-skills:**
   - `POST /api/sources/{id}/ingest?skill=entity-extract-only` — no wiki tools invoked
   - `POST /api/sources/{id}/ingest?skill=wiki-regenerate` — wiki only

---

## Risk Mitigations

| Risk | Mitigation |
|------|------------|
| **Alembic migration** | Use explicit DDL in `003_*` (not `create_all`); test `upgrade`/`downgrade` on `munger_test`; chain 001→002→003; document fresh install path |
| **pgvector on Pigsty** | Pre-flight `CREATE EXTENSION` in bootstrap scripts; fail fast in migration with clear error; verify on prod Pigsty before merge |
| **Backfill existing sources** | Idempotent `chunk_document` deletes old chunks first; delete stale mentions per source; document entity count drift; optional dry-run log in backfill |
| **Breaking ingest tests** | Update `test_ingest_agent.py`, `test_ingest_tool_gating.py`, `test_llm_adapter.py` in same PR as harness; single `INGEST_TOOL_ORDER` import |
| **Embedding dimension mismatch** | Config-driven `embedding_dimensions`; migration `vector(N)` matches; validate embed length in `chunk_service` before insert |
| **Extension permissions on munger_test** | Bootstrap uses admin URL for `CREATE EXTENSION`; grant to `munger_app` |
| **Long ingest / stale jobs** | Raise `max_agent_steps` to 30; consider `job_stale_minutes` bump; heartbeat during chunk prefix loop |
| **Zero-vector providers** | Fail `chunk_document` with clear error if provider cannot embed; document Ollama/OpenAI requirement for semantic AC |
| **Duplicate INGEST_TOOL_ORDER** | Single export from `ingest_tools.py`; middleware imports it |
| **Re-ingest duplicates** | `UNIQUE(source_id, chunk_index)` + delete-before-insert in chunk service |
| **Contextual prefix cost** | Sequential processing for cache; cap prefix tokens; fallback to raw embed on LLM failure |

---

## Work Objectives

1. Ship provenance-first 9+1 tool ingest pipeline in one release
2. Enable chunk-attributed semantic search via pgvector
3. Backfill existing sources without re-upload
4. Migrate four skills to DeerFlow format with sub-skill routing

## Guardrails

### Must Have

- All spec acceptance criteria (schema, tools, skills, retrieval, backfill, verification)
- Nullable `chunk_id` on legacy mentions
- `source_id`-only agent contract (optional params internal)
- No Neo4j, no GraphRAG CLI, no frontend provenance UI

### Must NOT Have

- Full graph rebuild on ingest
- SQLite paths
- Breaking production DB without migration
- Wipe-all re-ingest requirement

---

## Open Questions (User Confirmation)

See `.omc/plans/open-questions.md` for tracked items. Key decisions defaulted in ADR; confirm or `adjust`:

- Embedding dimension 768 vs 1536
- Wiki citation format (YAML + blockquote default)
- Backfill re-summarize yes/no
- Quality metric fail vs warn

---

## Handoff

**Plan saved to:** `.omx/plans/ralplan-enhance-ingestion-pipeline-provenance.md`

**Does this plan capture your intent?**

- **proceed** — Begin implementation via `/oh-my-claudecode:start-work ralplan-enhance-ingestion-pipeline-provenance`
- **adjust [X]** — Return to interview to modify
- **restart** — Discard and start fresh
