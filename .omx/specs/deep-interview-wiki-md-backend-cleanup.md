# Deep Interview Spec: Wiki Markdown Formatting + Backend Deprecated Cleanup

## Metadata

| Field | Value |
|-------|-------|
| Profile | Standard |
| Rounds | 5 |
| Final ambiguity | ~14% |
| Threshold | 20% |
| Context type | Brownfield |
| Context snapshot | `.omx/context/wiki-md-backend-cleanup-20260609T000000Z.md` |
| Transcript | `.omx/interviews/wiki-md-backend-cleanup-20260609T184900Z.md` |

## Clarity Breakdown

| Dimension | Score | Notes |
|-----------|-------|-------|
| Intent | 0.90 | Ship wiki readability + backend consolidation together |
| Outcome | 0.85 | Polished reading view + Postgres-only backend |
| Scope | 0.90 | Rich markdown stack; wikilink plugin only; no #tag/![[embed]] |
| Non-goals | 0.90 | No conservative retention of SQLite/workflow remnants |
| Constraints | 0.70 | Postgres production; dev frontend on :3000 |
| Success Criteria | 0.90 | Visual sample + tests/build + Alembic drop migration |
| Context (brownfield) | 0.90 | Codebase inventoried |

**Readiness gates:** Non-goals ✓ | Decision boundaries ✓ (inferred) | Pressure pass ✓ (round 4)

---

## Intent (Why)

Munger's wiki is the primary knowledge artifact, but pages render with ineffective typography despite existing `react-markdown`. In parallel, the backend still carries SQLite dev paths and WorkflowRun ORM/schema from the removed execution engine — misaligned with the Postgres + worker architecture. Both fixes are equally prioritized to restore reading quality and codebase honesty before next features.

## Desired Outcome

1. **Frontend:** Wiki detail pages render as a polished reading experience with GFM, math, syntax-highlighted code, and frontmatter support; `[[wikilinks]]` resolved via a custom remark plugin (not string pre-replacement).
2. **Backend:** Postgres-only application — SQLite code paths removed; Workflow/WorkflowRun/WorkflowRunStep models and tables removed via migration; dead docs/comments cleaned up.

## In-Scope

### Frontend (wiki reading view)

- Enhance `app/src/components/wiki/WikiMarkdown.tsx` and related wiki page shell
- Markdown pipeline (OMX may choose exact wiring; prefer extending existing `react-markdown` stack):
  - `remark-gfm` — tables, task lists, strikethrough
  - `remark-math` + `rehype-katex` — formulas
  - `rehype-highlight` or `shiki` — fenced code blocks
  - `gray-matter` — frontmatter parsing (metadata strip before render; optional display in sidebar)
  - Custom **remark plugin** for `[[wikilink]]` → internal `/wiki/:slug` links (replace or supersede `resolveWikiLinks()` string rewrite in `app/src/lib/wiki.ts`)
- Typography: install/configure `@tailwindcss/typography`; apply `font-wiki` (Merriweather) and Munger design tokens
- Custom component overrides for headings, tables, blockquotes, code blocks, images
- Verify on **localhost:3000** (Vite dev server)

### Backend (deprecated cleanup)

- **Remove SQLite support:**
  - `database.py` sqlite URL normalization, `is_sqlite_database()`, `init_db()` create_all path, pragma listener
  - `config.py` sqlite default `DATABASE_URL`
  - `sources.py` 503 guard for non-Postgres ingest (always Postgres)
  - `ingest_job.py` sqlite-specific index clause
  - `tests/conftest.py` sqlite test harness → Postgres test strategy (TEST_DATABASE_URL or docker)
  - Remove `aiosqlite` from requirements if unused
- **Remove workflow execution remnants:**
  - Delete `app/models/workflow.py` (Workflow, WorkflowRun, WorkflowRunStep)
  - Delete `app/workflow/` stub package
  - Remove model imports from `models/__init__.py`, `alembic/env.py`
  - Remove workflow seeding from `tests/conftest.py`
  - **Alembic migration `002_drop_workflow_tables`** — drop `workflow_run_steps`, `workflow_runs`, `workflows`
- **Docs/comments:** Update or remove `WORKFLOW_ARCH.md`, stale README workflow sections, `search.py` sqlite-vec comment
- **Keep (NOT deprecated):** Filesystem `SKILL.md` workflows under `data/workflows/` and `app/runtime/harness/skills/loader.py` — these power the ingest agent harness

## Out-of-Scope / Non-goals

- `#tag` parsing and tag index navigation
- `![[embed]]` transclusion
- MDX or editable wiki WYSIWYG
- Server-side markdown rendering (stay client-side)
- Wikilink alias/pipe syntax (`[[slug|Label]]`) unless trivially free
- Docker frontend rebuild (user devs on :3000)
- New ingest/worker features

## Decision Boundaries (OMX may decide without confirmation)

- Choose `react-markdown` + remark/rehype plugins vs full `unified` pipeline (bias: extend existing `react-markdown`)
- Choose `shiki` vs `rehype-highlight` for code blocks
- Exact prose/typography token mapping in Tailwind
- Postgres test harness approach (pytest + TEST_DATABASE_URL vs testcontainers)
- Order of migration vs code deletion within the spec
- Whether frontmatter displays in wiki sidebar or is parse-only

## Constraints

- React 19 + Vite frontend; FastAPI backend
- Production DB: Postgres on Pigsty
- Existing wikilink content uses `[[Page Title]]` format from LLM generation
- `listWikiPages({ page_size: 100 })` title map may need expansion or dedicated endpoint for wikilink resolution

## Testable Acceptance Criteria

1. **Visual:** A representative wiki page at `localhost:3000/wiki/:slug` shows styled headings, paragraphs, tables, fenced code with highlighting, and rendered math (if present in content).
2. **Wikilinks:** `[[Existing Page]]` renders as navigable internal link; unresolved links are visually distinct.
3. **Build:** `npm run build` and `npm run lint` pass in `app/`.
4. **Backend tests:** `pytest tests/ -v` passes with Postgres-only configuration (no sqlite URLs in test harness).
5. **No dead imports:** `rg -i 'WorkflowRun|is_sqlite|sqlite:///' munger/backend/app` returns zero hits (tests may reference TEST_DATABASE_URL postgres only).
6. **Migration:** Alembic `002_*` drops workflow tables; `alembic upgrade head` succeeds on existing `munger` database.
7. **SKILL.md harness:** Ingest agent still loads `default-ingest/SKILL.md` from filesystem after cleanup.

## Assumptions Exposed + Resolutions

| Assumption | Resolution |
|------------|------------|
| `@tailwindcss/typography` is the main formatting gap | Confirmed by codebase — `prose` classes present but plugin missing |
| User wants conservative cleanup | **Rejected** — full SQLite + workflow removal |
| SKILL.md on disk is deprecated | **Rejected** — keep harness skill loader; remove DB workflow models only |
| #tag and embed in this pass | **Rejected** — wikilink plugin only (round 4) |

## Pressure-Pass Findings

- **Round 4:** User initially listed `#tag` and `![[embed]]` plugins; under scope pressure, narrowed to **[[wikilink]] only** for this pass.

## Brownfield Evidence

- `WikiMarkdown.tsx` — react-markdown + remark-gfm only; prose classes without typography plugin
- `app/workflow/__init__.py` — "execution engine removed" stub
- `app/models/workflow.py` — WorkflowRun models still in schema; no API consumers
- `tests/conftest.py` — sqlite DATABASE_URL + Workflow seeding
- Harness `skills/loader.py` — active filesystem SKILL.md loader (keep)

## Technical Touchpoints

| Area | Files |
|------|-------|
| Wiki renderer | `app/src/components/wiki/WikiMarkdown.tsx`, `app/src/pages/WikiPage.tsx`, `app/src/lib/wiki.ts` |
| Tailwind | `app/tailwind.config.js`, `app/package.json` |
| DB layer | `munger/backend/app/core/database.py`, `config.py` |
| Workflow removal | `app/models/workflow.py`, `alembic/versions/002_*.py` |
| Tests | `munger/backend/tests/conftest.py`, `tests/test_sources_api.py` |

---

## Execution Bridge

Spec is ready. Recommended path:

```
$ralplan → $ralph (or $autopilot)
```

Do **not** implement directly from this interview.
