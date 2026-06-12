<!-- Generated: 2026-06-08 | Updated: 2026-06-08 -->

# Munger — Agent Reference (Cursor)

This file is auto-loaded in Cursor. It routes agents to the right docs — do not treat stale root archives or session folders as source of truth.

## Doc map (read in this order)

| Step | File | When to read |
|------|------|--------------|
| 1 | **This file** (`AGENTS.md`) | Always — conventions, ports, verify |
| 2 | Area `AGENTS.md` | Before editing that tree (see below) |
| 3 | Nested `AGENTS.md` | Before editing a specific subdirectory |
| 4 | [`ARCHITECTURE.md`](./ARCHITECTURE.md) | System design, ingest flow, data model |
| 5 | [`docs/ARCHITECTURE_DIAGRAMS.md`](./docs/ARCHITECTURE_DIAGRAMS.md) | As-built mermaid diagrams (architecture / ingest / ER / read-write paths) with code anchors |

**Area guides:**

- [`app/AGENTS.md`](./app/AGENTS.md) — React frontend package (see `app/src/AGENTS.md` for source tree)
- [`munger/AGENTS.md`](./munger/AGENTS.md) — Docker Compose, Pigsty Postgres, ports
- [`munger/backend/AGENTS.md`](./munger/backend/AGENTS.md) — FastAPI, worker, ingest agent, tests
- [`munger/frontend/AGENTS.md`](./munger/frontend/AGENTS.md) — nginx Docker image for production SPA

## Canonical vs archive vs session artifacts

| Path | Status | Agent policy |
|------|--------|--------------|
| `ARCHITECTURE.md` | **Canonical** | System truth for architecture questions |
| `AGENTS.md` tree | **Canonical** | Touchpoint maps and commands |
| `munger/backend/WORKFLOW_ARCH.md` | **Canonical** | Skill format + active vs dormant skills |
| `PLAN.md`, `SPEC.md` | **Archived** | Historical only — do not implement from these |
| `.omx/`, `.omc/` | **Session artifacts** | Planning output — never source of truth |
| `munger/data/wiki/` | **Generated runtime data** | Not dev documentation |

## Project structure

- `app/` — React 19 + TypeScript + Vite frontend (`app/src/`, `app/src/components/ui/`)
- `munger/` — Docker stack; backend in `munger/backend/`, nginx image in `munger/frontend/`

Keep utilities in `app/src/lib/`, screens in `app/src/pages/`, layout in `app/src/components/`.

## URLs and ports

| Surface | URL | Notes |
|---------|-----|-------|
| Frontend (dev) | `http://localhost:3000` | `npm run dev` in `app/` — preferred during UI work |
| Frontend (Docker) | `http://localhost:13000` | nginx container; may lag dev tree |
| Backend API | `http://localhost:18000` | `docker compose` default `BACKEND_PORT` |
| API docs | `http://localhost:18000/docs` | OpenAPI |

**Not current:** host API on `:8000`, Docker UI on `:3000` (stale in old docs).

## Verify commands

**Frontend** (from `app/`):

```bash
npm run build
npm run lint
```

**Backend** (from `munger/backend/`, Postgres required):

```bash
export TEST_DATABASE_URL=postgresql+psycopg://munger_app:PASSWORD@localhost:5432/munger_test
python scripts/bootstrap_test_postgres.py   # first-time only
pytest tests/ -v
```

Never point `TEST_DATABASE_URL` at the production `munger` database.

**Stack** (from `munger/`):

```bash
docker compose up -d
```

## Coding conventions

- TypeScript React function components; 2-space JSX indent; `PascalCase` components, `camelCase` hooks/functions
- Frontend imports: `@/*` alias; class merge via `cn()` in `app/src/lib/utils.ts`
- Backend: async FastAPI + SQLAlchemy; Postgres only (no SQLite paths)

## Testing

- Frontend: `npm run build` + `npm run lint`
- Backend: `pytest tests/ -v` with `TEST_DATABASE_URL` → `munger_test`
- Name tests after behavior: `test_sources_api.py`, `wiki-page.spec.tsx`

## Security

- Do not commit secrets or `.env` overrides
- API keys and LLM settings via environment variables
- `munger/backend/data/workflows/` = shipped skill **source**; `munger/data/` = runtime bind mount

## Commit & PR

Short imperative commits with scope when useful (`feat: add graph filters`). PRs: summary, commands run, screenshots for UI changes.
