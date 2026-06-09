# Ralplan: Wiki Markdown Formatting + Backend Deprecated Cleanup

**Source:** `.omx/specs/deep-interview-wiki-md-backend-cleanup.md`  
**Context:** `.omx/context/wiki-md-backend-cleanup-20260609T000000Z.md`  
**Mode:** Consensus (RALPLAN-DR deliberate — DB migration + destructive cleanup)  
**Status:** APPROVED v3 — Architect CONCERNS + Critic ITERATE addressed

---

## RALPLAN-DR Summary

### Principles
1. **Postgres is the only database** — no SQLite branches in app code or tests.
2. **Filesystem skills ≠ DB workflows** — delete Workflow ORM/tables; keep `SKILL.md` harness loader.
3. **Extend, don't replace** — build on existing `react-markdown` + `remark-gfm` stack.
4. **AST over string hacks** — `[[wikilink]]` via remark plugin, not `resolveWikiLinks()` regex rewrite.
5. **Verify both surfaces** — wiki visual on `:3000`; backend `pytest` + `alembic upgrade head`.

### Decision Drivers
1. **Destructive migration risk** — dropping `workflows*` tables on live Pigsty `munger` DB
2. **Test harness rewrite** — `conftest.py` is entirely SQLite `drop_all/create_all` today
3. **Bundle size / DX** — KaTeX CSS + highlighter choice affects wiki page load

### Viable Options

| Option | Pros | Cons |
|--------|------|------|
| **A (recommended):** react-markdown + remark/rehype plugins + rehype-highlight | Synchronous; trivial react-markdown integration | Less polished than shiki |
| **B:** Full unified pipeline | Maximum flexibility | Larger refactor; replaces working `WikiMarkdown` patterns |
| **C:** Keep SQLite tests, Postgres prod | Minimal test churn | Violates spec; dual-path maintenance continues |

**Invalidation:** B rejected — unnecessary rewrite. C rejected — user explicitly demanded SQLite removal.

### Pre-mortem (deliberate mode)

| Scenario | Mitigation |
|----------|------------|
| Alembic `002` drops tables still referenced | Grep all imports; run migration on copy of `munger` DB first; downgrade script optional |
| pytest fails without Pigsty running | `TEST_DATABASE_URL` required; document `docker compose up` + test DB bootstrap; skip marker only for optional integration tests |
| Wikilink plugin breaks existing pages | Keep fallback tests; plugin converts to md links before GFM parse; unresolved styling preserved |
| KaTeX/highlight breaks Vite build | Static KaTeX CSS import; `rehype-highlight` (sync); verify `npm run build` before merge |
| `gray-matter` Buffer breaks browser bundle | Use lightweight frontmatter regex splitter (mirror `loader.py`), not gray-matter |
| Test harness points at prod `munger` DB | Mandate `munger_test` only; abort if TEST_DATABASE_URL database name == `munger` |
| Coupled PR blocks rollback | Two merge units: (1) backend cleanup + migration, (2) wiki renderer — each independently verifiable |
| >100 wiki pages → broken wikilinks | PR1 raises wiki list cap; PR2 paginates slug-map fetch |
| `is_postgres_database` fan-out | Delete function; update `main.py`, `sources.py`, `worker/runner.py` together |

### Expanded Test Plan

| Layer | Coverage |
|-------|----------|
| **Unit** | `remark-wikilink` plugin: resolved/unresolved titles; `splitFrontmatter()` strip |
| **Integration** | `pytest` API tests on Postgres TEST_DATABASE_URL; ingest returns 202 |
| **E2E** | Manual: open `localhost:3000/wiki/:slug` — tables, code, math, wikilinks |
| **Observability** | `rg` zero-hit checks for `sqlite`, `WorkflowRun`; `alembic current` shows `002` |

---

## Requirements Summary

Ship two coupled deliverables in one pass:

1. **Frontend wiki reading view** — polished typography (Tailwind Typography), GFM, math, code highlighting, frontmatter parsing, custom `[[wikilink]]` remark plugin. Skip `#tag` and `![[embed]]`.
2. **Backend Postgres-only cleanup** — remove SQLite code paths, delete Workflow/WorkflowRun/WorkflowRunStep models, Alembic migration drops workflow tables, update tests and docs.

---

## Architecture

### Frontend markdown pipeline

```
WikiPage.tsx
  ├─ listWikiPages() → titleSlugMap (raise page_size or paginate)
  ├─ splitFrontmatter(page.content) → { data, content } (regex, no gray-matter)
  └─ WikiMarkdown
       ├─ remarkPlugins: [remarkGfm, remarkMath, remarkWikilink(map)]
       ├─ rehypePlugins: [rehypeKatex, rehypeHighlight]
       └─ components: custom h1-h6, pre, table, blockquote, img, a
```

**Library choices (OMX decision, documented in ADR):**
- Keep `react-markdown` v10
- Add `@tailwindcss/typography`, `remark-math`, `rehype-katex`, `rehype-highlight`, `highlight.js` CSS theme
- **No gray-matter** — browser-safe frontmatter splitter in `app/src/lib/frontmatter.ts`
- **shiki deferred** to follow-up (async init vs sync react-markdown render)
- Custom `remark-wikilink` in `app/src/lib/remark-wikilink.ts`

**Frontmatter:** Parse in `WikiPage.tsx`; show `title`, `tags`, `date` in sidebar if present (optional fields).

### Backend cleanup

```
Phase A: Migration 002_drop_workflow_tables
  └─ DROP workflow_run_steps, workflow_runs, workflows (IF EXISTS)

Phase B: Delete code
  ├─ app/models/workflow.py
  ├─ app/workflow/
  ├─ SQLite branches in database.py, config.py, main.py, sources.py, ingest_job.py
  └─ aiosqlite from requirements.txt

Phase C: Tests
  ├─ conftest.py → TEST_DATABASE_URL (postgresql+psycopg://.../munger_test)
  ├─ Session fixture: alembic upgrade head once; per-test TRUNCATE
  ├─ Remove Workflow seeding fixture
  └─ test_sources_api: ingest expects 202 (not 503)
```

**Keep:** `data/workflows/**/SKILL.md`, `app/runtime/harness/skills/loader.py`

---

## Implementation Phases

### Phase 1 — Backend migration + model removal (do first)

| Step | Task |
|------|------|
| 1.1 | Add `alembic/versions/002_drop_workflow_tables.py` — drop `workflow_run_steps` → `workflow_runs` → `workflows`; downgrade = explicit no-op |
| 1.2 | Delete `app/models/workflow.py`, `app/workflow/` |
| 1.3 | Remove workflow imports from `models/__init__.py`, `alembic/env.py` |
| 1.4 | Strip SQLite from `database.py` — Postgres-only URL normalization; delete `is_sqlite_database`, `is_postgres_database`, `init_db`, pragma |
| 1.5 | `config.py` default `DATABASE_URL` → Postgres DSN (match docker-compose) |
| 1.6 | `main.py` — always `run_migrations()`; remove `init_db`/`is_postgres_database` imports |
| 1.7 | `app/api/sources.py` — remove `is_postgres_database()` 503 guard + import (always enqueue, 202) |
| 1.8 | `app/worker/runner.py` — remove `is_postgres_database()` guard (Postgres is mandatory; worker fails at config if not) |
| 1.9 | `ingest_job.py` — remove `sqlite_where` from partial index |
| 1.10 | `app/api/wiki.py` — raise `page_size` cap to 500 (or add paginated slug-map helper for frontend) |
| 1.11 | Remove `aiosqlite` from `requirements.txt` |
| 1.12 | Clean `search.py` sqlite-vec comment; trim `WORKFLOW_ARCH.md` / README workflow engine sections |

### Phase 2 — Postgres test harness

| Step | Task |
|------|------|
| 2.1 | `conftest.py` — **require** `TEST_DATABASE_URL` → `munger_test` DB only; guard aborts if DB name is `munger` |
| 2.2 | Session fixture runs `alembic upgrade head` once; per-test `TRUNCATE` all tables (not `drop_all`); add `scripts/bootstrap_test_postgres.py` for `munger_test` |
| 2.3 | Remove Workflow fixture seeding |
| 2.4 | Update `test_sources_api.py` — ingest 202 + `job_id` present |
| 2.5 | Add `scripts/bootstrap_test_postgres.py` or document creating `munger_test` DB |

### Phase 3 — Frontend wiki renderer

| Step | Task |
|------|------|
| 3.1 | Install deps: `@tailwindcss/typography`, `remark-math`, `rehype-katex`, `rehype-highlight`, `katex` CSS |
| 3.2 | Configure typography plugin in `tailwind.config.js` |
| 3.3 | Implement `remark-wikilink.ts` — visit text nodes only (skip code); emit `/wiki/:slug` or `#unresolved` hrefs |
| 3.4 | Rewrite `WikiMarkdown.tsx` — plugin pipeline + component overrides + `font-wiki` |
| 3.5 | Update `WikiPage.tsx` — `splitFrontmatter()` from `frontmatter.ts`, pass map to plugin, optional frontmatter sidebar |
| 3.6 | Remove `resolveWikiLinks()` string rewrite from `wiki.ts` |
| 3.7 | `buildTitleSlugMap()` — paginated `listWikiPages` loop until all pages fetched (backend cap raised in 1.10) |

### Phase 4 — Verification

| Step | Task |
|------|------|
| 4.1 | `npm run build && npm run lint` in `app/` |
| 4.2 | `pytest tests/ -v` with `TEST_DATABASE_URL` set |
| 4.3 | `alembic upgrade head` on **`munger` DB snapshot/copy first**, then prod dev DB |
| 4.4 | `rg -i 'WorkflowRun|is_sqlite|is_postgres_database|sqlite:///' munger/backend/app` → 0 hits |
| 4.5 | Manual visual check on `localhost:3000/wiki/:slug` |

---

## Acceptance Criteria

- [ ] Wiki page shows styled prose, GFM tables, highlighted code fences, rendered `$...$` math
- [ ] `[[Existing Page]]` navigates to `/wiki/:slug`; unresolved links visually distinct
- [ ] `npm run build` passes
- [ ] `pytest tests/ -v` passes with Postgres `TEST_DATABASE_URL`
- [ ] No SQLite/workflow/`is_postgres_database`/`is_sqlite` references in `munger/backend/app`
- [ ] Alembic `002` applied; workflow tables gone from `\dt` in psql
- [ ] Ingest harness still loads `default-ingest/SKILL.md`

---

## ADR (Draft)

| Field | Decision |
|-------|----------|
| **Decision** | react-markdown + remark-wikilink + rehype-highlight + typography; Postgres-only backend; two PR merge units |
| **Drivers** | Existing stack, spec mandate, destructive cleanup, build-gate safety |
| **Alternatives** | unified pipeline (rejected); keep SQLite tests (rejected); shiki/gray-matter (deferred) |
| **Consequences** | Tests require Postgres + `munger_test` bootstrap; pytest no longer zero-infra |
| **Follow-ups** | shiki, #tag, ![[embed]], dedicated wiki slug-map API |

---

## Execution Staffing (post-approval)

### Merge units (recommended)

**PR 1 — Backend Postgres-only cleanup** (Phases 1–2 + 4 backend gates)  
**PR 2 — Wiki markdown renderer** (Phase 3 + 4 frontend gates)  
Each PR independently mergeable; do not block PR 2 on migration running in prod.

### `$ralph` (sequential)
PR 1 complete + verified → PR 2 complete + verified

### `$team` (parallel lanes — only if both PRs targeted same session)
| Lane | Owner | Scope |
|------|-------|-------|
| Backend cleanup | executor | PR 1 only |
| Wiki renderer | executor | PR 2 only (may start after PR 1 branch exists) |

**Verification:** test-engineer per PR; migration snapshot test before prod `munger`

### Suggested reasoning levels
- Migration/schema: high
- Markdown plugins: medium
- Typography CSS: low

### Available agent types
`executor`, `test-engineer`, `code-reviewer`, `verifier`

### Team launch hint
```
$team .omx/plans/ralplan-wiki-md-backend-cleanup.md
```

### Team verification path
1. `pytest tests/ -v` with TEST_DATABASE_URL
2. `npm run build`
3. Architect spot-check migration FK order
4. Manual wiki page screenshot review
