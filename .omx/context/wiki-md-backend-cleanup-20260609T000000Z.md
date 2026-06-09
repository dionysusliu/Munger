# Context Snapshot: Wiki Markdown + Backend Cleanup

**Created:** 2026-06-09T00:00:00Z  
**Task slug:** `wiki-md-backend-cleanup`

## Task Statement

1. Improve frontend wiki page rendering with better markdown formatting (markdown rendering libraries).
2. Audit backend and remove all deprecated logic.

## Desired Outcome (user-stated)

- Wiki pages look properly formatted (not plain/unstyled markdown).
- Backend codebase is lean — no leftover workflow engine, dead paths, or obsolete models.

## Probable Intent Hypothesis

- **Reading experience:** Munger wiki is the core knowledge artifact; poor typography undermines trust/usability.
- **Maintainability:** Recent ingest refactor (worker + Postgres + agent harness) left legacy workflow/SQLite cruft; user wants consolidation before next features.

## Known Facts (codebase evidence)

### Frontend wiki rendering
- Route: `app/src/pages/WikiPage.tsx` → `WikiMarkdown.tsx`
- Already uses `react-markdown` + `remark-gfm` (installed in `app/package.json`)
- `WikiMarkdown` applies Tailwind `prose` classes but **`@tailwindcss/typography` is NOT installed** — styles likely ineffective
- `font-wiki` (Merriweather) defined in `tailwind.config.js` but not used in wiki renderer
- Wikilinks: `resolveWikiLinks()` in `app/src/lib/wiki.ts` rewrites `[[Title]]` → `/wiki/slug`
- No syntax highlighting, minimal custom components (only `<a>` override)

### Backend deprecated / legacy inventory (initial)
| Item | Evidence |
|------|----------|
| Workflow execution engine | Removed; `app/workflow/__init__.py` is stub only |
| WorkflowRun models | `Workflow`, `WorkflowRun`, `WorkflowRunStep` still in `app/models/workflow.py`, Alembic `env.py`, DB schema |
| Outdated docs | `WORKFLOW_ARCH.md`, README workflow sections |
| SQLite dev path | Still in `database.py`, `config.py` default, tests (`conftest.py`); ingest queue returns 503 on SQLite |
| `sqlite-vec` comment | `app/api/search.py` references vector search via sqlite-vec (removed from requirements) |
| SKILL.md workflows | **Still active** — loaded by `app/runtime/harness/skills/loader.py` for ingest agent (NOT deprecated) |

## Constraints

- Brownfield React 19 + FastAPI stack
- Postgres is production DB; SQLite retained for tests?
- Docker frontend (13000) stale; dev on port 3000

## Unknowns / Open Questions

- What "better formatting" means visually (typography only vs code/math/diagrams)?
- Scope of backend cleanup: delete DB tables? migration? keep SQLite for tests?
- Are wiki formatting and backend cleanup one release or separate PRs?
- Non-goals not stated
- Decision boundaries not stated

## Likely Touchpoints

**Frontend:** `WikiMarkdown.tsx`, `WikiPage.tsx`, `tailwind.config.js`, `package.json`  
**Backend:** `app/models/workflow.py`, `app/workflow/`, Alembic migrations, `WORKFLOW_ARCH.md`, SQLite gating, search.py
