# Context Snapshot: Parallel chunk map-reduce + contextual retrieval

## Task statement
Read LightRAG (arXiv 2410.05779) for parallel chunking / map-reduce ideas, and read Anthropic contextual retrieval cookbook + post to implement contextual retrieval in Munger's ingestion pipeline.

## Desired outcome
A pipeline where stages remain ordered per document, but chunk-level work after splitting runs in parallel (map), then aggregates (reduce) — with production-grade contextual prefixes before embedding.

## Known facts (brownfield evidence)
- Munger has 9-tool linear agent gating (`IngestToolGatingMiddleware`) — one tool per step.
- `extract_entities_from_chunks` already uses `asyncio.gather` + `Semaphore(5)`.
- `chunk_document` contextual prefixes are **sequential**; embeddings batched via `embed_texts`.
- `glean_entities` is **sequential** per chunk.
- `resolve_entities` is the reduce/merge step (mentions + relationships).
- `chunk_service._contextual_prefix` sends full doc (12k cap) + chunk per call; **no prompt caching** wired.
- Ideas doc `munger-ingestion-pipeline-design.md` specifies parallel extraction + contextual prefix with caching.
- Anthropic cookbook: document-in-cache + parallel threads for chunk contextualization; 70–80% cache hit; embed batch 128.
- LightRAG: segment doc into chunks → per-chunk entity/relationship extraction (map) → dedupe/merge graph (reduce); incremental updates.

## Constraints
- Keep DeerFlow harness (SKILL + tool gating) unless spec says otherwise.
- Postgres/pgvector; provenance-first schema already landed.
- Ollama/local LLM may be default provider — prompt caching is provider-specific.

## Unknowns
- Target concurrency per stage (prefix vs extract vs glean)?
- Must contextual retrieval use Anthropic prompt caching, or is sequential doc reuse enough?
- Should map-reduce move **inside** services while keeping 9 tools, or split tools further?
- Rate-limit / heartbeat behavior for long parallel chunk phases?

## Likely touchpoints
- `munger/backend/app/services/chunk_service.py`
- `munger/backend/app/services/extraction_service.py`
- `munger/backend/app/services/resolution_service.py`
- `munger/backend/app/services/llm_service.py`
- `munger/backend/app/core/config.py` (concurrency knobs)
- `ideas/ingestion-pipeline/anthropic_contextual_retrieval_cookbook.html`
- `ideas/ingestion-pipeline/munger-ingestion-pipeline-design.md`
