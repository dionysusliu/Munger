# RALPLAN: Parallel Chunk Map-Reduce + Contextual Retrieval

**Slug:** `parallel-chunk-map-reduce-contextual`  
**Spec:** `.omc/specs/deep-dive-parallel-chunk-map-reduce-contextual.md`  
**Trace:** `.omc/specs/deep-dive-trace-parallel-chunk-map-reduce-contextual.md`  
**Prerequisite:** `.omx/plans/ralplan-enhance-ingestion-pipeline-provenance.md` (APPROVED v2, largely implemented)  
**Type:** Brownfield refactor (9-tool → 8-tool MAP/REDUCE)  
**Mode:** Consensus (RALPLAN-DR + ADR)  
**Date:** 2026-06-08  
**Status:** APPROVED v3.1 — Consensus complete

### Consensus Amendments (v2)

| Issue | Resolution |
|-------|------------|
| DB session per MAP worker | Each `gather` task opens **own** `async_session_maker()`; no shared session across workers |
| Prof merge scope | Merge descriptions **within source**; reconcile with existing global `Entity.description` (append/summarize, never blind overwrite) |
| Embedding batching | Hybrid MAP: workers compute prefixes in parallel → **single batched** `embed_texts()` → workers persist embeddings |
| REDUCE Prof concurrency | Semaphore-bounded parallel Prof merges (reuse worker concurrency default 5); skip-if-single |
| Backfill task | No tool-order change in `backfill_source` (enqueue only); verify deletion set unchanged |
| Alias bodies | Rewire `extract_entities_from_text` → `chunk_document` → `map_chunks` → `reduce_entities` |
| Acceptance test | Replace wall-clock ratio with **max concurrent workers observed** ≥2 under 10-chunk fixture |

### Critic Amendments (v3)

| Gap | Resolution |
|-----|------------|
| File paths | All paths prefixed `munger/backend/` (backend) or `app/` (frontend) |
| Backfill relationships | Add `delete(EntityRelationship)` in `backfill_source`; regression test required |
| `extract_entities_from_text` alias | Rewire to `chunk_document` → `map_chunks` → `reduce_entities` |
| Wave A persistence | Wave A workers persist `chunk_extractions`; Wave C only updates chunk prefix+embedding |
| Service wiring | Register `MapChunkService` in `RuntimeServices`; expose in `build_ingest_tools()` |
| MAP idempotency | `map_chunks()` deletes `ChunkExtraction` for source at start |
| Spec sync | Update spec wave diagram in Phase 1 entry (not deferred to Phase 3) |
| Heartbeat | Pass `job_id` from `ingest_tools.py` → `map_chunks()` → `touch_job_heartbeat` every 5 chunks |

---

## Executive Summary

Refactor the **already-shipped** provenance-first ingest pipeline from a 9-step linear tool chain (with partial internal parallelism) into an explicit **LightRAG-style map-reduce** model:

- **`chunk_document`** — split only (tiktoken + offsets, no LLM)
- **`map_chunks`** — hybrid MAP: Wave A parallel prefix+extract+glean → Wave B batched embed → Wave C persist
- **`reduce_entities`** — global dedupe + Prof description merge + provenance writes

Preserves DeerFlow harness, provenance schema, observability events, and sub-skill routing. Prompt caching deferred; parallel contextual prefix in v1.

---

## RALPLAN-DR Summary

### Principles

1. **Explicit map-reduce tools** — MAP and REDUCE are first-class gated tools, not hidden service internals.
2. **Chunk-worker parallelism** — Each chunk runs prefix+extract+glean end-to-end; semaphore bounds concurrency (default 5).
3. **Gleaning is a loop inside MAP** — Per-chunk reflective extract → YES/NO → CONTINUE; not a separate agent step.
4. **Harness preservation** — LangGraph agent + SKILL.md + `IngestToolGatingMiddleware`; `source_id`-only tool args.
5. **Brownfield-safe migration** — Alias deprecated tools one release; backfill path updated; no schema migration required.

### Decision Drivers (Top 3)

1. **Throughput on large documents** — Serial contextual prefix + glean dominate wall-clock for N chunks.
2. **User architecture choice** — Deep-dive interview selected explicit split tools + chunk workers + Prof REDUCE.
3. **LightRAG alignment** — Per-chunk Recog (MAP) then Dedupe+Prof (REDUCE) matches paper semantics.

### Viable Options

#### Option A: Explicit `map_chunks` + `reduce_entities` (chosen)

Replace `extract_entities_from_chunks`, `glean_entities`, `resolve_entities` with two tools; `chunk_document` becomes split-only.

| Pros | Cons |
|------|------|
| Matches user interview + trace recommendation | Breaks existing 9-tool skills/tests until updated |
| Clear operator observability (2 MAP/REDUCE steps) | Larger coordinated harness change |
| Full chunk-worker parallelism | Prof merge adds REDUCE LLM cost |

#### Option B: Keep 9 tools, parallelize inside services only

| Pros | Cons |
|------|------|
| Minimal harness/skill churn | Violates user "split tools" decision |
| Faster to ship | Agent gating still shows 3 serial MAP steps |

**Invalidation:** User explicitly chose split tools in deep-dive Round 1.

#### Option C: Worker bypass — agent triggers `ingest_map_reduce` monolith

| Pros | Cons |
|------|------|
| Simplest agent surface | Loses fine-grained gating and sub-skill routing |

**Invalidation:** Conflicts with DeerFlow harness and sub-skills (`entity-extract-only`, etc.).

---

## ADR: Chunk-Worker Map-Reduce with Parallel Contextual Prefix

### Decision

Implement **Option A**: 8-tool pipeline with explicit MAP/REDUCE, chunk-worker concurrency, GraphRAG-style glean loop inside MAP, Anthropic contextual prefix (parallel, no caching v1), and LightRAG Prof merge at REDUCE.

**Planner defaults** (resolve spec ambiguities):

| Topic | Default |
|-------|---------|
| Tool order | `parse_document` → `chunk_document` → `map_chunks` → `reduce_entities` → `summarize_source` → `generate_wiki_pages` → `link_wiki_pages` → `finalize_ingest` |
| Concurrency | `ingest_chunk_worker_concurrency = 5` (replaces `ingest_extract_concurrency` for MAP) |
| Glean loop | YES/NO gate with soft parse fallback; `max_gleanings` default 1 |
| Entity type dedup | Keep `(name.lower(), type)` key — no type vote in v1 |
| Prof merge | Within-source: concatenate colliding descriptions → LLM summarize; if global `Entity.description` exists, merge summaries (do not overwrite other sources' text) |
| Aliases (1 release) | `extract_entities_from_chunks` → `map_chunks`; `glean_entities` → `map_chunks`; `resolve_entities` → `reduce_entities` |
| `chunk_document` idempotency | Delete existing chunks for source before re-split; MAP deletes extractions before re-map |
| Heartbeat | Update `IngestJob.heartbeat_at` every N chunks inside MAP worker pool |
| `max_agent_steps` | Lower to **24** (8 core tools + headroom) |

### Drivers

- Deep-dive spec + trace evidence on serial prefix/glean bottleneck
- Prior provenance pipeline already has `chunks`, `chunk_extractions`, gating, observability

### Alternatives Considered

- Option B (hidden parallelism) — rejected (user scope)
- Option C (worker monolith) — rejected (harness/sub-skills)
- Phase-parallel waves (all prefix, then all extract) — rejected; chunk workers simpler and match interview

### Consequences

- **Positive:** ~O(N/5) MAP wall-clock; clearer operator timeline; LightRAG REDUCE parity for Prof
- **Negative:** Breaking change to tool order, skills, tests, Ingest.tsx step cards; Prof merge LLM cost at REDUCE
- **Neutral:** No new migration; prompt caching remains follow-up

### Follow-ups

- Anthropic `cache_control: ephemeral` on document block
- Entity-type majority vote
- `entities.embedding` at REDUCE
- Per-chunk timing benchmarks on 20+ chunk PDFs

---

## Implementation Phases

### Phase 1: Service Layer — MAP worker

**Goal:** `MapChunkService` (or refactored `chunk_service` + `extraction_service`) runs per-chunk worker end-to-end.

**Tasks:**

0. **Spec sync** — update `.omc/specs/deep-dive-parallel-chunk-map-reduce-contextual.md`:
   - L60–82: Wave A/B/C diagram (batched embed in Wave B; Wave A persists extractions)
   - L123–129: acceptance criteria → `max_observed_concurrency` metric (not wall-clock O(N/5))
1. **`chunk_service.split_chunks(source_id)`** — tiktoken split + persist rows **without** prefix/embed/LLM; delete prior chunks for source.
2. **`map_chunk_service.map_chunks(source_id, job_id)`** — hybrid chunk-worker MAP:
   - **Idempotency:** delete `ChunkExtraction` rows for source at start (mirror `extraction_service.py:82-84`)
   - **Wave A (parallel):** per-chunk workers run `_contextual_prefix` + `_extract_round_0` + `_glean_loop` (YES/NO → CONTINUE); each worker uses **dedicated AsyncSession** and **persists `chunk_extractions` + `contextual_prefix`** (mirror `extraction_service._one`)
   - **Wave B (batched):** collect `prefix + chunk` texts → single `embed_texts()` call
   - **Wave C:** update chunk rows with `embedding` only (prefix already in Wave A)
3. **Concurrency** — `asyncio.Semaphore(ingest_chunk_worker_concurrency)` + `gather`; instrument `max_observed_concurrency` metric
4. **Config** — add `ingest_chunk_worker_concurrency` (default 5); remove `ingest_extract_concurrency` (replaced); set `max_agent_steps=24`
5. **Service wiring** — register `MapChunkService` in `RuntimeServices.from_settings()`; expose via `build_ingest_tools()` as `map_chunks`
6. **Heartbeat** — `ingest_tools.map_chunks` passes `job_id`; service calls `touch_job_heartbeat(session, job_id)` every 5 chunks when `job_id is not None`

**Acceptance:**
- [ ] 10-chunk fixture with mocked delay: `max_observed_concurrency` ≥ 2 and ≤ `ingest_chunk_worker_concurrency`
- [ ] Each chunk has `contextual_prefix`, `embedding`, ≥1 `chunk_extraction` row
- [ ] Glean loop writes `glean_round=1` only when YES/NO gate returns YES

### Phase 2: Service Layer — REDUCE + Prof merge

**Goal:** `reduce_entities` replaces `resolve_entities` with Prof description merge.

**Tasks:**

1. Extend `resolution_service.reduce_entities(source_id)`:
   - Collect all instances per `(name.lower(), type)` from extractions (within source)
   - If multiple descriptions within source: concatenate → `llm.summarize` → candidate description
   - **Phase A (parallel):** group descriptions in memory; run within-source Prof merges under semaphore (default 5)
   - **Phase B (serial upsert):** `find_or_create` + mention/relationship writes in controlled session to avoid races
   - On `find_or_create`: if global entity has description, **reconcile** via LLM summarize of `{existing, candidate}` (≤512 tokens); never replace with source-only text silently
   - Existing mention/relationship upsert logic preserved
2. **Prof prompt** — short merge prompt (≤512 tokens out); skip LLM if single description

**Acceptance:**
- [ ] Re-run MAP+REDUCE on source: duplicate entity names get merged description, not first-only
- [ ] Relationship upsert still idempotent

### Phase 3: Tools, Gating, Skills

**Tasks:**

1. Update `INGEST_TOOL_ORDER` + `STEP_LABELS` in `pipeline_events.py`
2. Update `ingest_tools.py` — new `map_chunks`, `reduce_entities`; slim `chunk_document`
3. Update `TOOL_ALIASES` + rewire alias tool bodies (`extract_entities_from_text` → `chunk_document` → `map_chunks` → `reduce_entities`)
   - **Backward-compat scope (one release):** deprecated tools (`extract_entities_from_chunks`, `glean_entities`, `resolve_entities`) remain **registered** for gating normalization + unit tests only; skill `allowed_tools` uses new 8-tool names; composite aliases **not** in `allowed_tools` (normalization-only, not agent-callable in default ingest)
4. Rewrite `default-ingest/SKILL.md` — 8-tool order
5. Update sub-skills:
   - `entity-extract-only`: `parse` → `chunk` → `map` → `reduce`
   - `wiki-regenerate`: unchanged (post-reduce)
6. Update `sources.py` `backfill_source`: add `delete(EntityRelationship)` for `source_id`
7. Update `ingest_prompt.py`, tests (`test_ingest_agent`, `test_ingest_tool_gating`, `test_pipeline_events`, `test_backfill_source` relationship-cleanup)

**Acceptance:**
- [ ] Gating blocks `reduce_entities` before `map_chunks` completes
- [ ] Aliases normalize correctly

### Phase 4: Observability + Frontend

**Tasks:**

1. `map_chunks` metrics: `chunks_processed`, `entities_raw`, `glean_entities_added`, `worker_concurrency`, `duration_ms`
2. `reduce_entities` metrics: `entities_canonical`, `prof_merges`, `mentions_created`
3. Update `Ingest.tsx` `PIPELINE_STEPS` to 8 steps
4. (Backfill fix done in Phase 3 task 6)

**Acceptance:**
- [ ] Status API `current_step` shows "Mapping chunks" / "Merging entities"
- [ ] Ingest page N/8 progress

### Phase 5: Tests + Verification

**Tasks:**

1. `test_map_chunk_service.py` — glean loop YES/NO, semaphore concurrency
2. `test_reduce_prof_merge.py` — multi-description merge mocked
3. `pytest tests/ -v`; `npm run build`
4. Manual: 20+ chunk doc ingest; compare step durations

---

## Available Agent Types Roster

| Lane | Agent | Tier | Scope |
|------|-------|------|-------|
| Implementation | `executor` | STANDARD | Phases 1–3 services + tools |
| Frontend | `executor` | STANDARD | Phase 4 Ingest.tsx |
| Tests | `test-engineer` | STANDARD | Phase 5 |
| Verification | `verifier` | STANDARD | pytest + build evidence |
| Sign-off | `architect` | STANDARD | ADR compliance |

### Staffing Guidance

- **Ralph:** Sequential phases 1→2→3→4→5 with architect at end
- **Team:** Parallel after Phase 1 API frozen — executor(MAP) + executor(REDUCE) sequential; frontend parallel with Phase 3

### Launch Hints

```
/ralph .omx/plans/ralplan-parallel-chunk-map-reduce-contextual.md
```

---

## File Touch List

| File | Action |
|------|--------|
| `munger/backend/app/services/chunk_service.py` | Split `split_chunks` vs remove prefix from chunk_and_embed |
| `munger/backend/app/services/map_chunk_service.py` | **Create** — MAP worker orchestration |
| `munger/backend/app/services/extraction_service.py` | Refactor glean loop + extract into MAP worker |
| `munger/backend/app/services/resolution_service.py` | Rename/extend `reduce_entities` + Prof merge |
| `munger/backend/app/runtime/tools/ingest_tools.py` | New tools + order + `job_id` plumbing |
| `munger/backend/app/runtime/pipeline_events.py` | 8-step order + labels |
| `munger/backend/app/runtime/context.py` | Register `MapChunkService` in `RuntimeServices` |
| `munger/backend/app/core/config.py` | `ingest_chunk_worker_concurrency` |
| `munger/backend/data/workflows/default-ingest/SKILL.md` | 8-tool order |
| `munger/backend/data/workflows/entity-extract-only/SKILL.md` | 4-tool subset |
| `munger/backend/app/api/sources.py` | Backfill: add `EntityRelationship` delete |
| `app/src/pages/Ingest.tsx` | 8 pipeline steps |
| `.omc/specs/deep-dive-parallel-chunk-map-reduce-contextual.md` | Sync Wave A/B/C diagram |
| `munger/backend/tests/unit/test_map_chunk_service.py` | **Create** |
| `munger/backend/tests/unit/test_reduce_prof_merge.py` | **Create** |
| `munger/backend/tests/unit/test_backfill_source.py` | **Create** — relationship-cleanup regression |
