---
name: entity-extract-only
description: Extract and resolve entities with provenance — no summary or wiki steps.
allowed-tools:
  - parse_document
  - chunk_document
  - map_chunks
  - reduce_entities
tool-order:
  - parse_document
  - chunk_document
  - map_chunks
  - reduce_entities
---

# Entity Extraction Only

Extract named entities with chunk-level provenance without generating summaries or wiki pages.

## Tool order (mandatory)

1. **parse_document** — Extract plain text. Fatal if empty.
2. **chunk_document** — Split into token chunks (no LLM).
3. **map_chunks** — Parallel MAP: contextual prefix, extract, glean-loop, embed.
4. **reduce_entities** — Dedup, Prof-merge descriptions, write mentions.

## Arguments

Every tool accepts **only** `source_id`.
