# Munger Skill Architecture (DeerFlow-inspired)

## Core Insight

Munger uses **Skills** — declarative `SKILL.md` files with YAML frontmatter and Markdown methodology. The ingest agent runtime loads these skills from the filesystem and executes them through a LangGraph harness.

Key design patterns:
1. **Skill = Workflow Definition**: Human-readable markdown with structured metadata
2. **Parser**: Extracts YAML frontmatter and validates format (`app/runtime/harness/skills/loader.py`)
3. **Tool Policy**: Skills declare which tools they can use (`allowed-tools`)
4. **Agent Harness**: LangGraph lead agent with middleware, checkpointing, and ingest tools

## Skill Storage Format

```yaml
---
name: default-ingest
description: Default source ingestion pipeline
allowed-tools:
  - extract_source_text
  - summarize_source
  - extract_entities_from_text
  - create_wiki_pages
  - finalize_ingest
---

# Default Ingest

Methodology and instructions for the ingest agent...
```

Built-in skills live under `data/workflows/` (copied to `/app/builtin-workflows` in the Docker image). Custom skills can be added alongside them in `data/workflows/`.

## Runtime Architecture

```
Source upload
  └─ POST /api/sources/{id}/ingest → ingest_jobs queue
       └─ Worker claims job
            └─ Ingest lead agent (LangGraph)
                 ├─ load_skill("ingest") → default-ingest/SKILL.md
                 ├─ build_ingest_tools() → five ingest tools
                 └─ Middleware chain (tool gating, logging, etc.)
```

## Integration with Services

The ingest harness reuses:
- `LLMService` — provider abstraction
- `StorageService` — text extraction
- `EntityService` — entity extraction
- `WikiService` — wiki CRUD and links
- `SearchService` — index updates

Legacy DB-backed workflow execution (`workflows`, `workflow_runs`, `workflow_run_steps`) was removed in migration `002_drop_workflow`. Skills remain filesystem-only.

## Built-in Skills

| Skill | Path | Status | Purpose |
|-------|------|--------|---------|
| Default Ingest (`ingest`) | `data/workflows/default-ingest/SKILL.md` | **Active** | Ingest agent skill — loaded by worker on every ingest job |
| Munger 12-Dimension | `data/workflows/munger-12-dimension/SKILL.md` | **Dormant** | Legacy `{{step:…}}` file — not executed by runtime |
| Quick Summary | `data/workflows/quick-summary/SKILL.md` | **Dormant** | Legacy `{{step:…}}` file — not executed |
| Entity Extract Only | `data/workflows/entity-extract-only/SKILL.md` | **Dormant** | Legacy `{{step:…}}` file — not executed |

**Note:** Munger 12-dimension **analysis** is available via `POST /api/munger/analyze/{source_id}` (`munger_service.py`), not via the dormant SKILL file.
