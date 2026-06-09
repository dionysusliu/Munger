# Deep Dive Spec: enhance-ingestion-pipeline-provenance

**Slug:** `enhance-ingestion-pipeline-provenance`  
**Ambiguity:** 14% (threshold 20%)  
**Type:** Brownfield  
**Source:** deep-dive (trace + interview)

---

## Goal

Replace Munger's monolithic 5-tool ingest pipeline with a **provenance-first, chunk-indexed pipeline** inspired by `ideas/ingestion-pipeline/` — implementing contextual retrieval (Anthropic), Instructor structured extraction + gleaning (GraphRAG patterns), and LightRAG-style incremental graph/wiki updates — while preserving the existing DeerFlow harness architecture (vanilla LangGraph agent + SKILL.md + fine-grained tools).

The pipeline must support:
- Full 9-tool ingest workflow in one release
- Chunk-level provenance chain: `entity → chunk → source` with char offsets
- Wiki pages that cite specific chunk excerpts (not just entity-name grep)
- Contextual chunk embeddings + real pgvector semantic search
- Incremental entity/relationship merge (LightRAG pattern, no full graph rebuild)
- Backfill path for sources already ingested under v1

---

## Constraints

1. **Architecture:** Keep vanilla agent + SKILL/tool harness — no GraphRAG CLI, no LlamaIndex PropertyGraphIndex takeover. Tools call existing services layer.
2. **Database:** PostgreSQL + pgvector on Pigsty — no Neo4j. Single DB for relational, vector, and graph edges.
3. **Dependencies (lightweight):** Add `instructor`, `tiktoken`, `pgvector` (Python). Optional `graspologic` deferred unless community detection needed in this release.
4. **Harness:** Update `INGEST_TOOL_ORDER` in both `ingest_tools.py` and `ingest_tool_gating_middleware.py`; parameterize or extend gating for sub-skills.
5. **Migration:** Backfill existing sources — chunk `content_text` in-place, re-run extraction on chunks, regenerate wiki with chunk citations. Do not require full wipe.
6. **Backward compatibility:** Old `EntityMention` rows without `chunk_id` remain valid; backfill populates provenance. API should handle nullable `chunk_id` during transition.
7. **ID types:** Existing schema uses `int` PKs (`sources.id`, `entities.id`). New `chunks` table should use `int` FKs to match, not UUID (ideas doc UUIDs are illustrative — adapt to Munger conventions).
8. **LLM provider:** Reuse existing `LLMService` / Ollama-OpenAI bridge; Instructor wraps same provider.
9. **12-dimension analysis:** Remains separate path (`analyze_source_12d` tool + `munger-12-dimension` skill), not part of default ingest order.

---

## Non-Goals

- Full GraphRAG community detection / Leiden clustering in this release (optional Phase 3 later)
- Replacing wiki markdown renderer or frontend provenance UI (backend + data model first; minimal API exposure)
- Neo4j or separate vector database (Pinecone, Qdrant)
- LlamaIndex or GraphRAG library embedding
- WebSocket ingest progress (keep polling)
- Automatic re-ingest on LLM model change (manual trigger via `entity-extract-only` skill)

---

## Acceptance Criteria

### Schema & Provenance

- [ ] Alembic migration `003_*` adds `chunks`, `chunk_extractions` tables and extends `entity_mentions` with `chunk_id`, `char_start`, `char_end`
- [ ] Alembic migration enables `pgvector` extension and adds `embedding vector(N)` on `chunks` (+ optional on `entities`)
- [ ] `Chunk` and `ChunkExtraction` SQLAlchemy models registered in `app/models/__init__.py`
- [ ] Every new `EntityMention` created by ingest has non-null `chunk_id` + char offsets
- [ ] API `EntityMentionResponse` exposes `chunk_id`, `char_start`, `char_end`
- [ ] Provenance chain queryable: given `entity_id`, can list `source_id → chunk_id → excerpt`

### Tools (9 + 1)

- [ ] `parse_document(source_id)` — replaces `extract_source_text` (alias or rename with deprecation note)
- [ ] `chunk_document(source_id, chunk_size=600, overlap=100)` — tiktoken-based splitting; generates contextual prefix per chunk (Anthropic pattern); stores chunks + embeddings
- [ ] `extract_entities_from_chunks(source_id, max_concurrency=5)` — Instructor + Pydantic `ExtractionResult` per chunk; writes `chunk_extractions`
- [ ] `glean_entities(source_id, max_gleanings=1)` — second-pass extraction; appends to `chunk_extractions` with `glean_round=1`
- [ ] `resolve_entities(source_id)` — canonicalize names, embedding cosine block, cross-doc dedup; writes `entities` + `entity_mentions` with provenance
- [ ] `summarize_source(source_id)` — unchanged behavior
- [ ] `generate_wiki_pages(source_id)` — incremental; cites chunk excerpts in page content/frontmatter
- [ ] `link_wiki_pages(source_id)` — split from old `create_wiki_pages`; resolves `[[wikilinks]]`
- [ ] `finalize_ingest(source_id)` — unchanged contract; adds quality metric logging
- [ ] `analyze_source_12d(source_id)` — standalone tool for munger-12-dimension skill

### Harness & Skills

- [ ] `default-ingest/SKILL.md` rewritten with 9-tool order + quality metrics (entities/chunk ratio 3–15)
- [ ] `entity-extract-only/SKILL.md` migrated to DeerFlow format with `allowed-tools`
- [ ] `wiki-regenerate/SKILL.md` created (new)
- [ ] `munger-12-dimension/SKILL.md` migrated to DeerFlow format with `analyze_source_12d`
- [ ] `IngestToolGatingMiddleware` updated for 9-step order (or skill-parameterized order)
- [ ] `test_ingest_agent.py` updated for new tool count and order
- [ ] Sub-skill routing: ingest lead agent can load skill by job type (default vs entity-only vs wiki-regenerate)

### Retrieval

- [ ] `SearchService.semantic_search` queries `chunks.embedding` via pgvector cosine (`<=>`)
- [ ] `/api/search/semantic` returns chunk text + `source_id` + `chunk_id` attribution
- [ ] Hybrid search: FTS on `wiki_pages` + vector on `chunks` (LightRAG dual-level: local chunks + global entity/wiki)

### Relationships (LightRAG)

- [ ] `entity_relationships` table (or JSONB on entities) stores extracted edges from `chunk_extractions.relationships`
- [ ] Incremental merge: new ingest adds/updates relationships without rebuilding full graph
- [ ] `link_wiki_pages` uses relationship data to enrich `wiki_links` where applicable

### Backfill

- [ ] CLI or admin endpoint `POST /api/sources/{id}/backfill` chunks existing `content_text`, re-runs extract→glean→resolve→wiki
- [ ] Backfill preserves `source_id`; replaces stale mentions for that source

### Verification

- [ ] `pytest tests/ -v` in `munger/backend/` passes (new unit tests for chunking, Instructor schemas, provenance chain)
- [ ] `npm run build` in `app/` passes (if API types change)
- [ ] Manual: ingest a >10k char PDF; verify mentions have `chunk_id`; wiki page contains chunk citation block

---

## Assumptions Exposed

1. **Pigsty Postgres has or can install pgvector** — bootstrap script will `CREATE EXTENSION IF NOT EXISTS vector`
2. **Embedding dimension** matches provider (1536 for OpenAI `text-embedding-3-small`, configurable)
3. **600-token chunks** per GraphRAG paper — override for docs <1200 tokens
4. **Contextual prefix** generated at chunk time via LLM (50–100 tokens); cost acceptable with prompt caching on same document
5. **Entity resolution** uses embedding cosine + LLM confirm cascade (better than GraphRAG title+type only)
6. **Chunk IDs are int** aligned with existing Munger integer PK convention
7. **Re-ingest quality** on backfill may change entity counts — acceptable; user chose backfill over wipe

---

## Technical Context

### Current State (trace evidence)

| Area | Current | Gap |
|------|---------|-----|
| Tools | 5 monolithic `source_id`-only | Need 9 finer tools |
| `EntityMention` | `source_id` + 200-char doc prefix | No `chunk_id`, offsets |
| Chunking | `chunk_text()` unused | Wire tiktoken 600-token |
| Extraction | Single LLM pass, 10k truncate | Instructor per-chunk + gleaning |
| Search | `ILIKE` fallback | pgvector on `chunks.embedding` |
| Skills | 1 active, 3 dormant legacy format | 4 DeerFlow skills |
| pgvector | Not in requirements/bootstrap | Add extension + dep |

### Proposed Tool Module Layout

```
munger/backend/app/runtime/tools/
├── parsing.py              # parse_document
├── chunking.py             # chunk_document (+ contextual prefix + embed)
├── extraction.py           # extract_entities_from_chunks, glean_entities
├── resolution.py           # resolve_entities
├── summarization.py        # summarize_source
├── wiki_generation.py      # generate_wiki_pages, link_wiki_pages
├── finalization.py         # finalize_ingest
├── munger_analysis.py      # analyze_source_12d
└── schemas/
    ├── entity.py           # ExtractedEntity, ExtractionResult, GleanResult
    └── chunk.py            # ChunkMetadata
```

### Proposed Schema (adapted to int PKs)

```sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE chunks (
    id SERIAL PRIMARY KEY,
    source_id INTEGER NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    contextual_prefix TEXT,          -- Anthropic contextual retrieval
    token_count INTEGER NOT NULL,
    char_start INTEGER NOT NULL,
    char_end INTEGER NOT NULL,
    embedding vector(1536),
    created_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(source_id, chunk_index)
);

CREATE TABLE chunk_extractions (
    id SERIAL PRIMARY KEY,
    chunk_id INTEGER NOT NULL REFERENCES chunks(id) ON DELETE CASCADE,
    source_id INTEGER NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
    entities JSONB NOT NULL DEFAULT '[]',
    relationships JSONB NOT NULL DEFAULT '[]',
    glean_round INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE entity_relationships (
    id SERIAL PRIMARY KEY,
    source_entity_id INTEGER NOT NULL REFERENCES entities(id),
    target_entity_id INTEGER NOT NULL REFERENCES entities(id),
    relationship_type VARCHAR(50) NOT NULL,
    description TEXT,
    source_id INTEGER REFERENCES sources(id),
    chunk_id INTEGER REFERENCES chunks(id),
    created_at TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE entity_mentions
    ADD COLUMN chunk_id INTEGER REFERENCES chunks(id),
    ADD COLUMN char_start INTEGER,
    ADD COLUMN char_end INTEGER;

ALTER TABLE entities
    ADD COLUMN embedding vector(1536);  -- for cross-doc resolution
```

### Contextual Retrieval (in `chunk_document`)

Per Anthropic pattern: for each chunk, LLM generates 50–100 token situating context from full document; embed `contextual_prefix + "\n\n" + chunk.content`. Process chunks from same document sequentially to leverage prompt caching.

### Instructor Integration (in `extraction.py`)

```python
import instructor
from app.runtime.tools.schemas.entity import ExtractionResult, GleanResult

# Pydantic models: ExtractedEntity, ExtractedRelationship, ExtractionResult, GleanResult
# Gleaning prompts mirror GraphRAG CONTINUE_PROMPT / LOOP_PROMPT patterns
```

### LightRAG Patterns

- **Incremental entity merge:** `resolve_entities` upserts entities; no full table rebuild
- **Incremental wiki:** `generate_wiki_pages` touches only entities from current source's extractions
- **Dual-level retrieval:** chunk vectors (low-level) + entity/wiki FTS (high-level)
- **Relationship edges:** stored in `entity_relationships`, merged not rebuilt

### Postgres Sufficiency

PostgreSQL + pgvector is sufficient for:
- Chunk semantic search (cosine on `chunks.embedding`)
- Entity dedup embeddings (`entities.embedding`)
- Graph edges (`entity_relationships`, `wiki_links`)
- Provenance joins (`entity_mentions` → `chunks` → `sources`)

Neo4j not required unless multi-hop relationship analytics becomes a first-class product surface.

### Harness Changes

- `INGEST_TOOL_ORDER`: 9 steps matching `default-ingest` skill
- Gating middleware: consider `skill.tool_order` from SKILL frontmatter to support sub-skills with different orders
- `ingest_lead_agent.py`: accept `skill_name` parameter for job routing
- Deprecate old tool names with aliases during transition (`extract_source_text` → `parse_document`)

---

## Ontology

| Entity | Type | Key Fields | Relationships |
|--------|------|------------|---------------|
| Source | core domain | id, content_text, status | has many Chunks |
| Chunk | core domain | id, source_id, content, contextual_prefix, embedding, char_start/end | belongs to Source; has many ChunkExtractions, EntityMentions |
| ChunkExtraction | supporting | chunk_id, entities JSONB, relationships JSONB, glean_round | belongs to Chunk |
| Entity | core domain | name, type, description, embedding | has many EntityMentions, Relationships |
| EntityMention | core domain | entity_id, chunk_id, char_start, char_end | links Entity to Chunk |
| EntityRelationship | supporting | source_entity_id, target_entity_id, type, chunk_id | LightRAG edge |
| WikiPage | core domain | title, content, frontmatter.sources | cites Chunks; linked via WikiLink |
| IngestTool | harness | name, order, allowed-tools | orchestrated by SKILL |
| SKILL | harness | name, allowed-tools, steps | drives IngestTool sequence |

---

## Ontology Convergence

- **Stable:** Source, Entity, WikiPage (existing concepts, extended)
- **New:** Chunk, ChunkExtraction, EntityRelationship (from ideas doc, adapted)
- **Renamed:** extract_source_text → parse_document; create_wiki_pages → generate_wiki_pages + link_wiki_pages
- **Stability ratio:** High — entities map cleanly to ideas doc and existing ORM

---

## Trace Findings

**Most likely explanation:** Munger's ingest harness is a working v1 MVP (5 monolithic tools) but the provenance-first chunk-indexed pipeline from `ideas/ingestion-pipeline/` was never built. Schema, retrieval, and harness gaps are three facets of the same missing layer.

**Per-lane critical unknowns resolved by interview:**
- Phasing: **full pipeline in one spec** (user choice)
- Migration: **backfill chunks in-place** for existing sources
- Provenance bar: **wiki cites chunk excerpts** (not full audit trail of raw JSON)

**Evidence that shaped spec:**
- `EntityMention` lacks chunk provenance (`entity.py:37-50`)
- Semantic search stubbed to `ILIKE` (`search.py:203-212`)
- 5-tool order hardcoded in tools + middleware
- Ideas doc provides detailed tool/SKILL/schema designs — baseline, not yet implemented
- Postgres+pgvector sufficient; Neo4j rejected by design intent

**Trace artifact:** `.omc/specs/deep-dive-trace-enhance-ingestion-pipeline-provenance.md`

---

## Interview Transcript

### Round 1 — Goal Clarity (100% → ~48%)

**Q:** Given provenance-first priority, how should we phase this?  
**A:** Full pipeline in one spec — all 9 tools, pgvector, contextual retrieval, relationship extraction, sub-skills.

### Round 2 — Constraint Clarity (~48% → ~34%)

**Q:** For sources already ingested under the 5-tool pipeline, what should happen?  
**A:** Backfill — chunk existing `content_text` in-place, re-run extraction on chunks, preserve what we can.

### Round 3 — Success Criteria (~34% → ~14%)

**Q:** What is the minimum provenance bar for "done"?  
**A:** Every EntityMention has chunk_id + char offsets; wiki pages cite specific chunk excerpts.

---

## Execution Bridge

Spec ready at: `.omc/specs/deep-dive-enhance-ingestion-pipeline-provenance.md`  
Trace at: `.omc/specs/deep-dive-trace-enhance-ingestion-pipeline-provenance.md`  
Ambiguity: **14%**
