# Deep Dive Trace: enhance-ingestion-pipeline-provenance

## Observed Result

User wants to enhance Munger's ingestion pipeline using ideas from `ideas/ingestion-pipeline/` — Anthropic contextual retrieval, Instructor structured extraction, LightRAG incremental graph patterns — with **provenance-first** design, vanilla agents + SKILL/tool harness. Need to design tools, draft SKILLS, and evaluate whether PostgreSQL (+ pgvector) is sufficient for DB infra.

Current codebase runs a working DeerFlow-style ingest harness (5 monolithic `source_id`-only tools) but lacks chunk storage, chunk-level provenance, stored embeddings, contextual prefixes, gleaning/resolution, and real semantic search.

## Ranked Hypotheses

| Rank | Hypothesis | Confidence | Evidence Strength | Why it leads |
|------|------------|------------|-------------------|--------------|
| 1 | **Unified indexing gap** — provenance schema, retrieval/index, and harness granularity are three facets of one missing chunk-first pipeline (never built after v1 MVP) | High | Strong | All lanes independently confirm: no `chunks` table, no `chunk_id` on mentions, 5 coarse tools, vector search stubbed; ideas doc describes target state |
| 2 | **Schema/provenance is the binding constraint** — without `chunks` + `EntityMention.chunk_id`/`char_*`, provenance-first claims cannot be persisted regardless of extraction quality | High | Strong | `EntityMention` has `source_id` + blunt `context` prefix only (`entity.py:37-50`, `entity_service.py:114-134`) |
| 3 | **Harness coarseness blocks sub-skill orchestration** — 5 tools + hardcoded `INGEST_TOOL_ORDER` in tools and middleware prevent chunk→glean→resolve steps and dormant skill revival | High | Strong | `ingest_tools.py:21-27`, `ingest_tool_gating_middleware.py:16-22`, `default-ingest/SKILL.md` mirror 5-step order; dormant skills use legacy `{{step:…}}` format |
| 4 | **Postgres+pgvector is architecturally sufficient** — Neo4j not required; blocker is missing implementation not wrong DB | Medium | Moderate | Design doc rejects Neo4j; `wiki_links` + co-mention graph exist; no `vector` extension wired in app code |

## Evidence Summary by Hypothesis

### Hypothesis 1 (Unified indexing gap)

- Ingest path: extract → summarize → entities (whole doc) → wiki → finalize (`ARCHITECTURE.md`, `ingest_tools.py`)
- `chunk_text()` exists in `text_utils.py` but has **zero ingest call sites**
- `ingest.chunk_size` / `ingest.chunk_overlap` config seeded but never read by ingest services
- `LLMService.extract_entities` truncates to 10k chars, single pass, "most important only" prompt (`llm_service.py:542-558`)
- Semantic search API explicitly falls back to `ILIKE` (`search.py:203-212`); `SearchService.semantic_search` generates embedding then discards it (`search_service.py:244-255`)
- Ideas doc (`munger-ingestion-pipeline-design.md`) proposes 9 tools, `chunks`/`chunk_extractions` tables, Instructor schemas, contextual embeddings — **proposal only**

### Hypothesis 2 (Schema/provenance)

- `EntityMention`: no `chunk_id`, `char_start`, `char_end` (`entity.py:37-50`)
- Mention creation stores first 200 chars of full doc, not entity-local offset (`entity_service.py:114-134`)
- Design target: `entity_id → chunk_id → source_id` provenance chain (`ideas doc §provenance`)
- Alembic head `002_drop_workflow`; no `Chunk` ORM model in `app/models/__init__.py`

### Hypothesis 3 (Harness granularity)

- Exactly 5 tools registered and tested (`test_ingest_agent.py`)
- `IngestToolGatingMiddleware` exposes one tool at a time from fixed order
- Active skill `default-ingest/SKILL.md` lists only 5 `allowed-tools`
- Dormant skills (`entity-extract-only`, `quick-summary`, `munger-12-dimension`) incompatible with DeerFlow frontmatter format
- No `instructor`, `tiktoken`, `glean`, `chunk_document` in backend codebase
- `wiki-regenerate` skill proposed in design doc but not shipped

### Hypothesis 4 (Postgres sufficiency)

- Wiki graph via `wiki_links` + entity co-mention (`entity_service.py:238-261`)
- Entity dedup is name+type, not embedding-based (`entity_service.py:78-87`)
- Design doc: Postgres + pgvector + optional `graspologic` for Phase 3 community detection
- No `pgvector` in `requirements.txt`; no `CREATE EXTENSION vector` in bootstrap scripts
- Pigsty pgvector install status **unverified** in repo

## Evidence Against / Missing Evidence

- **Source-level provenance exists today** — `EntityMention.source_id` links entities to documents (weakens "no provenance" but not chunk-level claim)
- **Wiki-time context extraction** — `_extract_entity_context` uses 800-char window at render time (`ingest_tools.py:30-37`) but not persisted on mentions
- **Embedding client exists** — `LLMService.embed_text` works but store-never, query-never
- **Harness shell is modular** — skill loader, tool policy, middleware chain ready for extension without architectural rewrite
- **12-dimension analysis is separate** — `POST /api/munger/analyze/{source_id}` may not need ingest tool split
- **No production benchmark** — entity recall gap on large docs unmeasured (impact of coarseness unproven at runtime)

## Per-Lane Critical Unknowns

- **Lane 1 (Schema/provenance):** Which failure mode dominates first on long sources — (A) inability to store chunk/offset provenance, or (B) monolithic extraction quality loss from 10k truncation + single-pass recall — and whether fixing only one half unblocks the pipeline?
- **Lane 2 (Retrieval/indexing):** Whether the Pigsty Postgres instance already has the `vector` extension installed and ready (design doc asserts yes, app code never enables it).
- **Lane 3 (Harness granularity):** Whether the current 5-tool pipeline measurably under-extracts entities on large documents versus chunk+glean, and whether that gap justifies 9-tool harness expansion over service-internal chunking.

## Rebuttal Round

- **Best rebuttal to leader (unified gap):** "Harness coarseness is intentional v1 — hide chunking inside `extract_entities_from_text` and keep 5 tools; only add schema + pgvector."
- **Why leader held:** Sub-skill orchestration (`entity-extract-only`, `wiki-regenerate`), step-level observability (design doc quality metrics per step), and provenance persistence at extraction time all require **observable, gatable boundaries** that service-internal chunking cannot expose. Gating middleware and SKILL are hardcoded to five names in two files. Schema changes (`chunks`, `chunk_extractions`, `EntityMention.chunk_id`) are coupled to when chunk boundaries are created — that boundary is naturally a tool step, not a hidden service detail.

## Convergence / Separation Notes

- **All three lanes converge** on the same root cause: the chunk-first provenance-indexed pipeline described in `ideas/ingestion-pipeline/` was designed but never implemented; current system is whole-document ingest + FTS.
- **Lanes separate on fix locus:** Lane 3 asks whether behavior can stay inside services (H2) vs must surface as finer tools (H1); benchmark discriminates.
- **Postgres vs Neo4j is settled in design intent** — implementation gap, not architectural indecision.
- **Contextual retrieval + LightRAG** are design targets only; no code generates contextual chunk prefixes or extracted relationship edges.

## Most Likely Explanation

Munger's ingest harness is a **working v1 MVP** (DeerFlow-style agent + 5 monolithic tools) that successfully produces wiki pages and entity mentions at **document granularity**, but the **provenance-first chunk-indexed pipeline** from `ideas/ingestion-pipeline/` was never built. Schema (`chunks`, chunk-level `EntityMention`), retrieval (contextual embeddings, pgvector), and harness (9 finer tools, Instructor gleaning, sub-skills) are **three views of the same missing layer**, not three independent problems. PostgreSQL + pgvector is sufficient; Neo4j is not required for the stated direction.

## Critical Unknown

**Phased rollout scope:** Should implementation deliver the full 9-tool + schema + pgvector + contextual retrieval pipeline in one release, or phase it (e.g., Phase 1: `chunks` + provenance schema + chunk-then-extract; Phase 2: contextual embeddings + vector search; Phase 3: LightRAG relationship graph + community detection)? This determines tool/SKILL count, migration risk, and backward compatibility with existing ingested sources.

## Recommended Discriminating Probe

**Two-part probe before spec lock:**

1. **DB probe** (collapses Lane 2 unknown):
   ```sql
   SELECT extname FROM pg_extension WHERE extname = 'vector';
   SELECT table_name FROM information_schema.tables
   WHERE table_name IN ('chunks', 'chunk_extractions');
   ```

2. **Recall A/B** (collapses Lane 1 + Lane 3 unknowns): On one fixture source with `len(content_text) > 10_000`, compare current `extract_from_text` vs offline `chunk_text` + per-chunk `extract_entities` — measure entity recall and whether mentions can be mapped to source offsets.

If schema probe shows no pgvector and A/B shows large recall gap, spec should prioritize Phase 1 (chunks + provenance + chunk-then-extract tools) before LightRAG community layer.
