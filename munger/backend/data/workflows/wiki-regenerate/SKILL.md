---
name: wiki-regenerate
description: Regenerate wiki pages and links from existing entity extractions.
allowed-tools:
  - generate_wiki_pages
  - link_wiki_pages
tool-order:
  - generate_wiki_pages
  - link_wiki_pages
---

# Wiki Regenerate

Rebuild wiki pages and cross-links for entities already extracted from a source.

## Tool order (mandatory)

1. **generate_wiki_pages** — Create or update entity wiki pages with chunk citations.
2. **link_wiki_pages** — Cross-link related entity pages.

## Arguments

Every tool accepts **only** `source_id`.
