---
name: ingest
description: Provenance-first ingest pipeline — chunk, map, reduce, wiki.
allowed-tools:
  - parse_document
  - chunk_document
  - map_chunks
  - reduce_entities
  - summarize_source
  - generate_wiki_pages
  - link_wiki_pages
  - finalize_ingest
tool-order:
  - parse_document
  - chunk_document
  - map_chunks
  - reduce_entities
  - summarize_source
  - generate_wiki_pages
  - link_wiki_pages
  - finalize_ingest
---

# Default Ingest Workflow

Process uploaded sources into provenance-linked entities and wiki pages.

## Tool order (mandatory)

Call exactly one tool per step:

1. **parse_document** — Extract plain text. Fatal if empty.
2. **chunk_document** — Split into token chunks (no LLM).
3. **map_chunks** — Parallel MAP: contextual prefix, extract, glean-loop, embed.
4. **reduce_entities** — Dedup, Prof-merge descriptions, write mentions.
5. **summarize_source** — Document summary (non-fatal on failure).
6. **generate_wiki_pages** — Entity + summary wiki with chunk citations.
7. **link_wiki_pages** — Cross-link related entity pages.
8. **finalize_ingest** — Index update, completion, quality metrics.

## Arguments

Every tool accepts **only** `source_id`.

## Quality

Target entities/chunk ratio 3–15. Logged in finalize step.
