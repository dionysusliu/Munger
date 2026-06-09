# Deep Dive Spec: update-md-agent-reference

## Goal

Restructure Munger markdown documentation so **Cursor agents** get reliable, discoverable reference material via a layered `AGENTS.md` tree — without rewriting archive bodies or touching session artifacts.

## Constraints

- **Audience:** Cursor agents only (`AGENTS.md` auto-load + nested hierarchy)
- **Archive policy:** `PLAN.md` and `SPEC.md` get superseded headers only — **no body rewrites**
- **Non-goals (explicit):**
  - Do not edit `.omx/`, `.omc/`, `ideas/`
  - Do not edit `munger/data/wiki/` generated content
  - Do not rewrite `PLAN.md` / `SPEC.md` bodies
- **Canonical system truth:** `ARCHITECTURE.md` — nested docs link to it, do not duplicate full architecture
- **Human docs:** `munger/README.md` and `munger/backend/README.md` get banner + trim stale SQLite/workflow sections; keep human quick-start where accurate

## Non-Goals

- OMX-specific session artifact documentation (`.omx/` README)
- Full rewrite of long product READMEs
- Updating `app/info.md`, `design/`, or generated wiki pages
- Implementing unwired frontend routes (document as unwired only)
- Rewiring dormant `SKILL.md` files to runtime

## Deliverables

### 1. Root `AGENTS.md` (expand into router)

Must include:

| Section | Content |
|---------|---------|
| Doc map | Read order: `AGENTS.md` → area `AGENTS.md` → `ARCHITECTURE.md` for system truth |
| Canonical vs archive | `ARCHITECTURE.md` = truth; `PLAN.md`/`SPEC.md` = archived snapshots |
| Session artifacts | `.omx/`, `.omc/` = planning session output, never source of truth |
| Dev URLs | Frontend dev `:3000`, API `:18000`, Docker UI `:13000` |
| Verify commands | `npm run build`, `pytest` with `TEST_DATABASE_URL` → `munger_test` |
| Pointers | Links to nested `app/AGENTS.md`, `munger/AGENTS.md`, `munger/backend/AGENTS.md` |

### 2. Nested `AGENTS.md` files (create)

**`app/AGENTS.md`** (`<!-- Parent: ../AGENTS.md -->`)

- Stack: React 19, Vite, Tailwind, shadcn/ui
- Wired routes only: `/`, `/ingest`, `/wiki`, `/wiki/:slug`
- Unwired pages: Search, Entities, Graph, Analysis, Settings, Logs (do not implement unless asked)
- Key files: `App.tsx`, `lib/api.ts`, `components/wiki/WikiMarkdown.tsx`, `lib/remark-wikilink.ts`
- Dev: `npm run dev` → `:3000`; API default `http://localhost:18000`
- Verify: `npm run build`, `npm run lint`

**`munger/AGENTS.md`** (`<!-- Parent: ../AGENTS.md -->`)

- Docker Compose stack: db-init, backend, worker, frontend
- Postgres on Pigsty (`docker_default` network), not bundled DB
- Port map table (host → service)
- `munger/.env` from `.env.example`; secrets not committed
- Data bind mount: `munger/data/` (runtime sources/wiki/schema exports)
- Commands: `docker compose up -d` from `munger/`

**`munger/backend/AGENTS.md`** (`<!-- Parent: ../../AGENTS.md -->`)

- Layer map: `api/` → `services/` → `models/` → `runtime/`
- Ingest path: `POST /sources/{id}/ingest` → `ingest_jobs` → worker → `IngestRunner`
- **Active skill:** `data/workflows/default-ingest/SKILL.md` (`ingest`)
- **Dormant skills:** `munger-12-dimension`, `quick-summary`, `entity-extract-only` (legacy `{{step:}}`, not executed)
- Five ingest tools + enforced order (reference `ingest_tools.py`)
- Tests: `TEST_DATABASE_URL` required, `munger_test` only, `bootstrap_test_postgres.py`
- Verify: `pytest tests/ -v`
- Postgres-only; no SQLite, no `/api/workflows`

### 3. Archive headers

Add to top of `PLAN.md` and `SPEC.md`:

```markdown
> **ARCHIVED** — Historical snapshot. For current architecture read [ARCHITECTURE.md](./ARCHITECTURE.md) and [AGENTS.md](./AGENTS.md). Do not implement from this file.
```

### 4. README trims (human-facing, agent-benefit)

| File | Action |
|------|--------|
| `README.md` (root) | Create minimal pointer: what Munger is, link to `ARCHITECTURE.md`, `AGENTS.md`, `munger/README.md` |
| `munger/README.md` | Banner at top; remove/trim SQLite, workflow API, `{{step:}}` runnable workflow claims, wrong ports (`:8000` host API → `:18000`) |
| `munger/backend/README.md` | Same trim as munger README (dedupe or cross-link) |
| `app/README.md` | Replace Vite boilerplate with Munger frontend pointer → `../AGENTS.md` + `app/AGENTS.md` |

### 5. `WORKFLOW_ARCH.md` update

- Mark `default-ingest` as **active** (ingest agent)
- Mark other three skills as **legacy / not wired**
- Remove implication all four are peer production workflows

## Acceptance Criteria

- [ ] Four-file `AGENTS.md` tree exists: root, `app/`, `munger/`, `munger/backend/`
- [ ] Root `AGENTS.md` contains doc map, archive policy, port table, verify commands
- [ ] `PLAN.md` and `SPEC.md` have archive banners; bodies unchanged
- [ ] `munger/README.md` and `munger/backend/README.md` trimmed of SQLite/workflow-API stale claims; banner present
- [ ] Root `README.md` and `app/README.md` are Munger-specific pointers (not empty/Vite template)
- [ ] `WORKFLOW_ARCH.md` distinguishes active vs dormant skills
- [ ] **Agent smoke test passes:** fresh Cursor agent given only `AGENTS.md` tree (no `ARCHITECTURE.md`) correctly answers:
  - Frontend dev URL `:3000`, Docker UI `:13000`, API `:18000`
  - Tests need `munger_test` via `TEST_DATABASE_URL`
  - One active ingest skill (`default-ingest`); three legacy SKILL files
  - Four wired frontend routes; Analysis page not wired
  - Does **not** cite SQLite, `/api/workflows`, or WebSocket as current

## Assumptions Exposed

- Cursor auto-loads root `AGENTS.md` only; nested files loaded when agents navigate or are told to read them
- `ARCHITECTURE.md` remains the deep system reference; nested `AGENTS.md` files are touchpoint maps
- `munger/README.md` human quick-start stays useful after trim (Docker, env, basic usage)
- Agent smoke test is manual (user or reviewer runs prompt), not CI-automated in this pass

## Technical Context

<trace-context>
Trace found flat doc mis-routing: thin auto-loaded AGENTS.md, no hierarchy, stale PLAN/SPEC/README discoverable, ARCHITECTURE.md correct but not in default surface. Coverage gaps: ports, munger_test, active vs dormant skills, unwired routes, wiki DB vs export paths.
</trace-context>

Current accurate reference: `ARCHITECTURE.md` (Postgres, worker queue, LangGraph ingest, 5 tools, 1 active skill).

Key code anchors:
- `app/src/App.tsx` — 4 routes
- `munger/docker-compose.yml` — ports 13000/18000
- `munger/backend/tests/conftest.py` — munger_test guard
- `munger/backend/app/runtime/agents/ingest_lead_agent.py` — `load_skill("ingest")`
- `munger/backend/data/workflows/default-ingest/SKILL.md` — active skill

## Ontology

| Entity | Role |
|--------|------|
| `AGENTS.md` tree | Agent entry-point docs (Cursor auto-load) |
| `ARCHITECTURE.md` | Canonical system truth (deep reference) |
| `PLAN.md` / `SPEC.md` | Archived snapshots (header only) |
| `.omx/` / `.omc/` | Session artifacts (out of scope) |
| `SKILL.md` | Filesystem skill definitions (1 active, 3 legacy) |
| `munger/data/wiki/` | Generated export (not dev docs) |

## Ontology Convergence

Stable after 6 interview rounds. User locked: Cursor-only audience, layered AGENTS.md, README trim, WORKFLOW_ARCH update, narrow non-goals, agent smoke acceptance.

## Trace Findings

See `.omc/specs/deep-dive-trace-update-md-agent-reference.md`.

**Most likely explanation:** Missing doc router at agent entry point causes stale root/README content to compete with `ARCHITECTURE.md`.

**Resolved unknowns:**
- Audience: Cursor agents only
- Scope: 4-layer AGENTS.md + README trim + WORKFLOW_ARCH + archive headers
- Archives: PLAN/SPEC headers only
- Verification: agent smoke test

## Interview Transcript

| Round | Question | Answer |
|-------|----------|--------|
| 1 | Doc audience? | Cursor agents only |
| 2 | File scope? | Layered AGENTS.md (root + app + munger + backend) |
| 3 | README policy? | Banner + trim stale workflow/SQLite; minimal root README |
| 4 | WORKFLOW_ARCH? | Update WORKFLOW_ARCH + backend AGENTS summary |
| 5 | Non-goals? | Narrow — skip .omx, ideas, wiki data; no PLAN/SPEC body edits |
| 6 | Acceptance? | Agent smoke test |

**Final ambiguity:** ~12% (≤ 20% threshold)
