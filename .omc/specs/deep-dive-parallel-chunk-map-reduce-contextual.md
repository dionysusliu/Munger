# Spec: Parallel Chunk Map-Reduce + Contextual Retrieval

**Slug:** `parallel-chunk-map-reduce-contextual`  
**Type:** Brownfield enhancement to Munger ingest pipeline  
**Ambiguity at crystallization:** ~15%  
**Trace:** `.omc/specs/deep-dive-trace-parallel-chunk-map-reduce-contextual.md`

---

## Goal

Refactor Munger ingestion to follow **LightRAG-style map-reduce** with **explicit MAP and REDUCE tools**, parallelizing per-chunk work after document splitting, then aggregating into canonical entities with provenance.

Incorporate **Anthropic contextual retrieval** (contextual prefix before embedding) with **parallel prefix generation** in v1; prompt caching deferred.

---

## Trace Findings

| Finding | Evidence |
|---------|----------|
| Agent/tool pipeline is linear (9-step gating) | `IngestToolGatingMiddleware` |
| Only `extract_entities_from_chunks` parallelizes today | `extraction_service.py` Semaphore+gather |
| Contextual prefix + glean are serial per chunk | `chunk_service.py`, `glean_entities` for-loop |
| `resolve_entities` = dedupe REDUCE, not Prof merge | `entity_service.find_or_create` keeps first description |
| No prompt caching in LLM layer | `llm_service.py` no `cache_control` |

---

## Constraints

1. **Explicit split tools** — expose MAP/REDUCE to agent gating (not hidden inside monolithic services only).
2. **Chunk-worker parallelism** — each chunk runs end-to-end: contextual prefix → extract → glean-loop; bounded by semaphore (default **5**).
3. **Gleaning is a per-chunk loop**, not a one-shot step:
   - Round 0: structured extract
   - Round N: feed prior entities + chunk → YES/NO gate → if YES, CONTINUE/"MANY entities missed" prompt → append glean_round extractions
   - `max_gleanings` configurable (default **1**)
4. **Contextual retrieval v1:** parallel prefix generation; **no prompt caching** requirement in v1 (caching is follow-up).
5. **REDUCE includes Prof merge** — LightRAG-style description summarization when merging duplicate entities.
6. Preserve provenance schema (`chunk_id`, char offsets, `chunk_extractions`).

---

## Non-Goals (v1)

- Anthropic `cache_control: ephemeral` / 70% cache-hit optimization
- LightRAG dual-level retrieval (local/global keyword graph retrieval)
- Leiden community detection
- Changing worker-level multi-document concurrency model
- Neo4j / external graph DB

---

## Proposed Tool Pipeline (replaces 9-tool MAP region)

| Step | Tool | Behavior |
|------|------|----------|
| 1 | `parse_document` | Unchanged |
| 2 | `chunk_document` | **Split only** — tiktoken segments + char offsets; no LLM |
| 3 | `map_chunks` | **MAP** — Wave A: parallel prefix+extract+glean → Wave B: batched embed → Wave C: persist embeddings |
| 4 | `reduce_entities` | **REDUCE** — dedupe entities/edges, Prof-merge descriptions, write mentions + relationships |
| 5 | `summarize_source` | Unchanged |
| 6 | `generate_wiki_pages` | Unchanged (may consume Prof-merged descriptions) |
| 7 | `link_wiki_pages` | Unchanged |
| 8 | `finalize_ingest` | Unchanged |

**Deprecate** as separate gated steps: `extract_entities_from_chunks`, `glean_entities`, `resolve_entities` (folded into map/reduce; keep aliases one release).

---

## MAP Tool: `map_chunks`

### Hybrid MAP waves (semaphore=5)

```
Wave A (parallel per-chunk workers, dedicated AsyncSession each):
  1. contextual_prefix(full_doc, chunk)
  2. extract_round_0 → chunk_extractions(glean_round=0)
  3. glean loop: YES/NO gate → if YES, CONTINUE → chunk_extractions(glean_round=1)
  4. persist contextual_prefix on chunk row + all extraction rows

Wave B (batched):
  5. embed_texts([prefix + chunk for all chunks])

Wave C:
  6. update chunk.embedding for all chunks
```

### Config

| Setting | Default |
|---------|---------|
| `ingest_chunk_worker_concurrency` | 5 |
| `ingest_max_gleanings` | 1 |
| `ingest_chunk_size_tokens` | 600 |
| `ingest_chunk_overlap_tokens` | 100 |

### Observability

Emit `pipeline_step` metrics: `chunks_processed`, `prefix_ms`, `extract_entities_raw`, `glean_entities_added`, `worker_concurrency`.

---

## REDUCE Tool: `reduce_entities`

1. Delete prior `entity_mentions` + `entity_relationships` for `source_id`
2. Load all `chunk_extractions` for source (all glean rounds)
3. **Dedupe** entities by canonical name (+ type policy TBD: keep separate types or vote)
4. **Prof merge:** for duplicate entity instances, concatenate descriptions → LLM summarize → update `Entity.description`
5. Write `EntityMention` with provenance (chunk_id, char offsets)
6. Upsert `EntityRelationship` (existing quad unique constraint)

---

## Contextual Retrieval (v1)

- Prompt template from Anthropic post/cookbook: situate chunk within document; answer only with succinct context
- Structure: `<document>...</document><chunk>...</chunk>` in user message
- **Parallel** `asyncio.gather` + semaphore (mirror extraction pattern)
- Embed `contextual_prefix + chunk` (already stored on `chunks.contextual_prefix`)
- **Deferred:** `cache_control: ephemeral` on document block for Anthropic API cost reduction

---

## Acceptance Criteria

- [ ] `map_chunks` reports `max_observed_concurrency` ≥2 and ≤`ingest_chunk_worker_concurrency` under 10-chunk mocked-delay fixture
- [ ] Glean loop implements YES/NO gate + CONTINUE per GraphRAG/LightRAG semantics; `max_gleanings` respected
- [ ] `reduce_entities` performs dedupe **and** LLM Prof description merge
- [ ] Agent gating enforces new tool order; skills updated
- [ ] `pipeline_step` events emitted for map_chunks + reduce_entities
- [ ] `pytest` covers glean loop logic (mocked LLM) and parallel semaphore behavior
- [ ] Backward-compat aliases for old tool names one release

---

## Assumptions Exposed

- Default LLM may be Ollama — parallel prefix works without caching; YES/NO logit_bias may be unavailable on non-OpenAI providers (soft fallback to free-text YES/NO parse)
- Prof merge adds LLM cost at REDUCE proportional to unique entity count
- `chunk_document` split-only keeps MAP idempotent: re-run deletes prior chunks/extractions for source

---

## Technical Context

| File | Change |
|------|--------|
| `app/services/chunk_service.py` | Split: `split_chunks()` vs `map_chunk_worker()` |
| `app/services/extraction_service.py` | Glean loop + extract in worker; remove separate glean tool path |
| `app/services/resolution_service.py` | Prof merge in reduce |
| `app/runtime/tools/ingest_tools.py` | New `map_chunks`, `reduce_entities`; update order |
| `app/runtime/pipeline_events.py` | New step labels |
| `app/core/config.py` | `ingest_chunk_worker_concurrency` |
| `data/workflows/default-ingest/SKILL.md` | New tool order |

---

## Ontology

| Entity | Role |
|--------|------|
| Document (Source) | Input; `content_text` immutable after parse |
| Chunk | MAP unit; contextual_prefix + embedding |
| ChunkExtraction | Per-chunk per-glean-round JSON |
| Entity | Canonical node after REDUCE |
| EntityMention | Provenance edge source→chunk→entity |

---

## Interview Transcript

| Round | Question | Answer |
|-------|----------|--------|
| 1 | Orchestration model | **Split tools** — explicit MAP/REDUCE in gating |
| 2 | MAP tool split | **Custom:** glean is reflective multi-round loop inside extract procedure, not one-shot step |
| 3 | Parallelism model | **Chunk workers + shared REDUCE** — each chunk end-to-end in parallel |
| 4 | Contextual retrieval | **Parallel prefix only v1** — skip prompt caching for now |
| 5 | REDUCE scope | **Dedupe + Prof merge** (LightRAG-style description summarization) |
| 6 | Concurrency | **5** concurrent chunk workers |

---

## Follow-ups (post-v1)

- Anthropic prompt caching on document block (`cache_control: ephemeral`)
- Entity-type majority vote at REDUCE
- `entities.embedding` population at REDUCE
- Phase-parallel wave mode if cache-hit rate makes it cheaper than chunk workers
