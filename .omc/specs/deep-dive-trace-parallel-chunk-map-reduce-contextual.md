# Deep Dive Trace: parallel-chunk-map-reduce-contextual

## Observed Result
User wants Munger ingest to follow LightRAG-style **map-reduce**: parallel per-chunk processing after splitting, then aggregate — plus Anthropic **contextual retrieval** (cached doc prefix + contextualized embeddings) per the cookbook/post.

Current Munger pipeline is **linear at the agent/tool level** (9-step gating) but only **partially parallel inside services**.

## Ranked Hypotheses

| Rank | Hypothesis | Confidence | Evidence Strength | Why it leads |
|------|------------|------------|-------------------|--------------|
| 1 | Munger implements LightRAG **MAP partially**: only `extract_entities_from_chunks` is parallel; contextual prefix + glean are serial | High | Strong | `asyncio.gather` only in extraction_service; serial `for` in chunk_service + glean |
| 2 | Munger implements LightRAG **REDUCE partially**: `resolve_entities` = dedupe merge, not Prof/description merge | High | Strong | `find_or_create` keeps first description; no LLM entity profiling in reduce |
| 3 | Contextual retrieval diverges from Anthropic cookbook: no prompt caching, sequential prefix loop | High | Strong | No `cache_control` in llm_service; serial `await` in chunk_and_embed |

## Evidence Summary by Hypothesis

### H1 — MAP parallelism gap
- **FOR:** `extraction_service.py:90-110` — `Semaphore(5)` + `gather` on chunks.
- **FOR:** `chunk_service.py:116-120` — sequential `await _contextual_prefix` per segment.
- **FOR:** `extraction_service.py:127-166` — sequential glean per chunk (data-independent across chunks).
- **AGAINST:** `embed_texts` is batched (not per-chunk serial LLM).
- **LightRAG paper:** segments doc → `Recog()` per chunk → dedupe merge. Munger matches shape but not full parallel MAP.

### H2 — REDUCE alignment
- **FOR:** Pipeline order extract → glean → resolve matches LightRAG extract → glean → merge.
- **FOR:** `find_or_create` + relationship `on_conflict_do_update` ≈ dedupe/edge merge.
- **AGAINST:** No description concatenation + LLM summarize (LightRAG Prof); no type vote; `Entity.embedding` unused in resolve.
- **AGAINST:** Wiki generation is downstream narrative, not KV entity profile merge.

### H3 — Contextual retrieval gap
- **FOR:** Cookbook uses `cache_control: ephemeral` on full document + `ThreadPoolExecutor` parallel threads.
- **FOR:** Munger `_contextual_prefix` puts doc in user message, truncated 12k, no cache markers.
- **AGAINST:** Short docs (single chunk) reduce caching benefit; non-Anthropic providers may not support caching.

## Per-Lane Critical Unknowns

- **Lane 1 (MAP):** Are serial prefix/glean loops a deliberate rate-limit choice or an unimplemented parallelism gap?
- **Lane 2 (REDUCE):** Is missing Prof/description merge intentional (wiki handles synthesis) or a LightRAG parity gap?
- **Lane 3 (Contextual):** What is the production LLM provider — is Anthropic prompt caching available on the ingest path?

## Rebuttal Round

- **Challenge:** "LightRAG MAP = Recog only, and Munger already parallelizes extraction — so we're done."
- **Verdict:** Recog is parallel, but the user's desired model includes **all per-chunk LLM work** (contextual prefix, extract, glean) before reduce. Two of three MAP loops remain serial.

## Convergence / Separation Notes

- MAP gap (H1) and contextual gap (H3) overlap in `chunk_document` but are separable fixes: parallelism vs caching API shape.
- REDUCE gap (H2) is independent — can parallelize MAP without changing resolve semantics.

## Most Likely Explanation

Munger's architecture is **staged map-reduce in spirit** (chunk → per-chunk work → `resolve_entities` reduce) but **incomplete in execution**: only entity extraction uses bounded parallelism. Contextual prefix and gleaning should be parallelized to match LightRAG MAP economics and the user's intent. Contextual retrieval needs prompt-cache-aware LLM calls (Anthropic) or an equivalent doc-reuse strategy. Reduce step handles dedupe but not LightRAG-style entity description profiling.

## Critical Unknown

**Orchestration preference:** Keep 9 linear agent tools with map-reduce hidden inside services, or expose explicit map/reduce tools to the agent?

## Recommended Discriminating Probe

Run ingest on a 20+ chunk source with `pipeline_step` duration metrics; compare wall-clock of `chunk_document` vs `extract_entities_from_chunks` vs `glean_entities`. If chunk+glean scale ~linearly with chunk count while extract scales ~1/concurrency, parallelizing prefix+glean is the highest-impact fix.
