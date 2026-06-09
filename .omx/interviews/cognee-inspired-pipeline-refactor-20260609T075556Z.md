# Deep Interview Transcript: Cognee-inspired pipeline refactor

**Profile:** Standard | **Rounds:** 7 | **Final ambiguity:** 14% | **Threshold:** 20%  
**Type:** Brownfield | **Context snapshot:** `.omx/context/cognee-inspired-pipeline-refactor-20260609T065210Z.md`

## Summary

User wants to refactor Munger's ingestion pipeline using Cognee as an architectural reference while keeping LangGraph/LangChain. Primary pain is **not chunk volume** but **entity reduce/cross-chunk linking** — merging candidates and building credible references (explicit mentions vs semantic neighbors). Outcome is **richer wiki pages** with auto wikilinks and related-pages sidebar.

## Q&A

### R1 — Intent
**Q:** Primary pain driver?  
**A:** Unified ingestion pipeline; scalable on large inputs; current pipeline too complex to scale.

### R2 — Intent (pressure)
**Q:** Where does it break on large inputs?  
**A:** Not chunk count (20MB/500pg books → few concepts). Real difficulty is reduce: cross-chunk entity merge + credible cross-references; may need later dedicated pass. No GDB — Postgres RDB+VDB only.

### R3 — Outcome
**Q:** What should linking produce?  
**A:** Richer wiki — auto `[[wikilinks]]` and related-pages sidebar from entity graph.

### R4 — Scope
**Q:** Which Cognee layers to adopt?  
**A:** Keep LangGraph; staged `add`/`cognify` as subgraphs. Detailed pipeline: input expansion (pdf/txt/md), ingest+register with content hash, Document wrap, chunk, per-chunk summarize/extract/embed, cross-chunk link (fuzzy+semantic+dedup), entity wiki generation. Outputs: chunks, VDB summaries, wiki pages.

### R5 — Non-goals
**Q:** Explicitly out of scope?  
**A:** No GDB; no public lifecycle API; no dir/S3 batch (single-file v1); no Tavily; no datalake format. Frontend/API breaking changes not excluded.

### R6 — Decision boundaries
**Q:** What may agent decide without asking?  
**A:** Schema migrations, replace tool gating with subgraphs, chunk algorithm, linking heuristics, deprecate legacy aliases, API v2 with v1 shim. **Must follow diagram:** `ideas/ingestion-pipeline/Untitled-2026-06-05-1654.png`. Subgraphs in separate files. Reconsider chunk/vector state storage.

### R7 — Success criteria
**Q:** Storage split + quality bar?  
**A:** **Keep all chunk text in Postgres** (exception to diagram FS/Lake for chunks). Discuss datalake portability in planning phase.

## Residual risks

- Cross-chunk linking algorithm unspecified beyond fuzzy + semantic + hybrid rank
- No quantitative perf SLA yet
- Enrichment deferred but cognify stage originally included Tavily — confirm no web enrichment in v1
- Frontend changes implicitly in scope (not excluded) but not specified
