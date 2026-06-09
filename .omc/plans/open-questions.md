# Open Questions — Munger Plans

## enhance-ingestion-pipeline-provenance - 2026-06-08

- [ ] **Embedding dimension at migration time** — Planner default: 768 (`nomic-embed-text`). Alternative: 1536 (OpenAI `text-embedding-3-small`). Changing later requires destructive migration. — Affects `alembic/versions/003_*` and `app/core/config.py`
- [ ] **Wiki chunk citation format** — Planner default: YAML frontmatter array + blockquote excerpt. Alternatives: inline `(source:chunk_id:char_start-char_end)`, fenced code only. — Drives `generate_wiki_pages` prompt and manual verification AC
- [ ] **Backfill re-summarize** — Planner default: yes (include `summarize_source` in backfill). Alternative: skip summarize when `content_summary` exists. — Affects backfill job tool subset
- [ ] **Quality metric `entities/chunk` ratio** — Planner default: log warning only outside 3–15. Alternative: fail `finalize_ingest`. — Affects ingest reliability vs strictness
- [ ] **Contextual prefix LLM failure** — Planner default: skip prefix, embed raw chunk with warning. Alternative: fail `chunk_document`. — Affects ingest resilience vs provenance quality
- [ ] **Hybrid search UX** — Planner default: single merged RRF list with `result_type` discriminator. Alternative: separate chunk vs wiki result buckets. — Affects `app/api/search.py` response shape
- [ ] **Cross-doc entity merge on backfill** — When resolution merges into global entity, regenerate wiki from all sources or only backfilled source? — Affects `wiki_generation.py` incremental scope
- [ ] **Deprecation window for aliases** — Planner default: keep `extract_source_text` / `create_wiki_pages` one release. Alternative: hard cutover. — Affects gating middleware and tests
- [ ] **Backfill auth** — No admin guard today on `sources.py`. Add auth or internal-only? — Security for `POST /api/sources/{id}/backfill`
- [ ] **Re-ingest completed source via `/ingest`** — Wipe chunks first (planner default) or reject if provenance exists? — Affects idempotency contract
