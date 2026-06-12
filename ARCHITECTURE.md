# Munger Architecture

Munger is an automated knowledge base: upload sources, run an LLM-powered ingest pipeline, and browse an interconnected wiki. The design draws on Karpathy’s LLM Wiki idea and Munger-style multi-perspective analysis.

This document describes how the system is structured today — for operators and developers, not as an API reference.

---

## Repository layout

The repo splits into two cooperating trees:

| Area | Path | Role |
|------|------|------|
| **Frontend** | `app/` | React 19 + TypeScript + Vite SPA |
| **Stack** | `munger/` | Docker Compose, backend API, worker, nginx frontend image |

```
Munger/
├── app/                    # Frontend source (dev: npm run dev → :3000)
│   └── src/
│       ├── pages/          # Route screens (Dashboard, Ingest, Wiki, …)
│       ├── components/     # Layout, wiki renderer, shadcn/ui primitives
│       └── lib/            # API client, wiki helpers, remark plugins
└── munger/
    ├── docker-compose.yml  # Backend, worker, db-init, frontend container
    ├── backend/            # FastAPI + ingest agent runtime
    │   ├── app/            # Application code
    │   ├── alembic/        # Postgres migrations
    │   └── data/workflows/ # SKILL.md skill definitions (filesystem)
    └── frontend/           # Nginx image build (prod: :13000)
```

---

## Runtime topology

Local full stack runs via Docker Compose in `munger/`. Postgres lives on **Pigsty** (external `docker_default` network); Munger does not ship its own database container.

```
┌─────────────────────────────────────────────────────────────────┐
│                         Browser                                  │
│   Dev:  http://localhost:3000   (Vite, app/)                    │
│   Prod: http://localhost:13000  (nginx, munger-frontend)        │
└────────────────────────────┬────────────────────────────────────┘
                             │ REST
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  munger-backend (:18000 → :8000)                               │
│  FastAPI — sources, wiki, entities, search, munger, config      │
└────────────┬───────────────────────────────┬────────────────────┘
             │                               │
             │ enqueue ingest_jobs           │ read/write
             ▼                               ▼
┌────────────────────────┐      ┌───────────────────────────────┐
│  munger-worker         │      │  Postgres (Pigsty)            │
│  claims jobs, runs     │      │  munger DB + LangGraph          │
│  LangGraph ingest agent│      │  checkpointer tables          │
└────────────────────────┘      └───────────────────────────────┘
             │
             ▼
┌────────────────────────┐
│  ./munger/data/        │  sources/, wiki/, workflows/ (bind mount)
└────────────────────────┘
```

**Bootstrap:** `munger-db-init` runs once to create the app user and `munger` database on Pigsty.

**Processes:**

| Container | Command | Responsibility |
|-----------|---------|----------------|
| `munger-backend` | `uvicorn` | HTTP API, migrations on startup |
| `munger-worker` | `python -m app.worker` | Poll `ingest_jobs`, run ingest agent |
| `munger-frontend` | nginx | Serve built SPA (may lag dev tree) |
| `munger-db-init` | `bootstrap_postgres.py` | One-shot DB setup |

---

## Backend architecture

### Layering

```
HTTP (FastAPI)
  app/api/          → route handlers
  app/schemas/      → Pydantic request/response models
  app/services/     → business logic (LLM, wiki, entities, storage, search)
  app/models/       → SQLAlchemy ORM
  app/core/         → config, database session, settings

Async jobs
  app/worker/       → job loop (claim → execute → complete)
  app/runtime/      → LangGraph ingest agent harness
    agents/         → ingest lead agent factory
    tools/          → five ingest StructuredTools
    harness/        → SKILL loader, middleware, checkpointer
    events/         → ingest timeline persistence
```

**Database:** Postgres only. Alembic runs on API startup (`001_initial` creates schema from ORM; `002_drop_workflow` removed legacy workflow tables). Tests use a separate `munger_test` database.

### API surface

All routes live under `/api`:

| Prefix | Purpose |
|--------|---------|
| `/sources` | Upload, list, ingest trigger, status/timeline, delete |
| `/wiki` | CRUD, slug lookup, links, related pages |
| `/entities` | List, detail, mentions, related |
| `/search` | Full-text search and suggest |
| `/munger` | 12-dimension analysis (separate from ingest agent) |
| `/config` | Runtime LLM and ingest settings |
| `/health`, `/stats` | System health and counts (`main.py`) |

Ingest is **asynchronous**: `POST /api/sources/{id}/ingest` returns **202** with a `job_id`. The worker executes the job; the UI polls `GET /api/sources/{id}/status` for `status` and `events[]`.

### Domain model (Postgres)

| Model | Role |
|-------|------|
| `Source` | Uploaded file metadata, extracted text, summary, status |
| `WikiPage`, `WikiLink` | Generated wiki content and cross-links |
| `Entity`, `EntityMention` | Extracted concepts/people/etc. tied to sources or pages |
| `MungerAnalysis` | Stored 12-dimension analysis results |
| `IngestJob` | Durable ingest queue (pending → running → completed/failed) |
| `IngestEvent` | Timeline events (status changes, agent messages, tool calls) |
| `IngestionLog` | Audit log entries |
| `Config` | Key-value settings (LLM provider, ingest flags, …) |

Source files stay on disk under `DATA_DIR/sources/`; the DB holds metadata and extracted text.

---

## Ingest pipeline (LangGraph subgraphs)

Ingest is the core automation path. Default orchestration is a **compiled LangGraph parent graph** with two subgraphs (`add`, `cognify`) in `app/runtime/graphs/`. Set `INGEST_ORCHESTRATOR=agent` to use the legacy LLM agent + tool-gating path.

### Storage (unified Postgres)

All ingest artifacts live on **one Postgres instance** (Pigsty + pgvector):

| Layer | Tables / columns |
|-------|------------------|
| RDB | `sources`, `chunks` (metadata + `content` text), `entities`, `entity_mentions`, `entity_relationships`, `wiki_pages` |
| VDB | `chunks.embedding`, `entities.embedding` (pgvector) |

Chunk text stays in `chunks.content` (not FS/Lake). Entity relationships are the graph — no separate graph DB.

Vector access goes through the `VectorStore` seam (`app/services/vector_store.py`), selected by
`VECTOR_BACKEND`: `pgvector` (default) reads/writes the embedding columns above; `lancedb` keeps
vectors in a LanceDB dataset at `LANCEDB_URI` (single-writer: the worker writes, API reads).
The pg embedding columns stay in place until a future cutover SP; move data between backends with
`scripts/migrate_vectors.py --to lancedb|pgvector`.

### Graph steps (`GRAPH_STEP_ORDER`)

`register_source` → `parse_document` → `hash_dedup` → `chunk_document` → `map_chunks` (Send fan-out per chunk when `INGEST_MAP_MODE=send`) → `reduce_entities` → `link_entities` → `summarize_source` → `generate_wiki_pages` → `link_wiki_pages` → `finalize_ingest`

### Execution flow

```
POST /sources/{id}/ingest
  → enqueue IngestJob (status: pending)
  → worker claims job
  → IngestRunner.run(source_id, job_id)
       → build_ingest_graph(services, checkpointer)   [default]
       → add subgraph: register → parse → hash_dedup
       → cognify subgraph: chunk → map (Send) → reduce → link → summarize → wiki → finalize
       → IngestEvent rows via pipeline_step wrappers
  → job status: completed | failed
```

**Services:** `StorageService`, `LLMService`, `ChunkService`, `MapChunkService`, `ResolutionService`, `LinkingService`, `WikiService`.

**Completion signals:**

- Backend: `Source.status == "completed"` (or `"failed"`) after `finalize_ingest` or `fail_source`
- Queue: `IngestJob.status == "completed"` in worker `finally`
- Frontend: polling stops when source status is terminal

### Munger 12-dimension analysis

This is a **separate path**: `POST /api/munger/analyze/{source_id}` via `munger_service.py`. It does not run through the ingest skill/tool chain. The `munger-12-dimension/SKILL.md` file describes the analytical framework but is not executed by the worker today.

---

## Frontend architecture

### Stack

- React 19, TypeScript, Vite, Tailwind CSS, shadcn/ui
- HashRouter (`#/wiki/...`) for static hosting compatibility
- API base URL: `VITE_BACKEND_BASE_URL` or default `http://localhost:18000`

### Routes (implemented)

| Route | Page | Backend |
|-------|------|---------|
| `/` | Dashboard | stats, recent activity |
| `/ingest` | Ingest | sources upload, ingest trigger, status poll, timeline |
| `/wiki` | Wiki browser | list pages |
| `/wiki/:slug` | Wiki reader | page by slug |

Additional pages exist in `app/src/pages/` (Search, Entities, Graph, Analysis, Settings, Logs) but are not wired in `App.tsx` yet.

### Wiki rendering

`WikiPage` loads content from the API, splits YAML frontmatter (`lib/frontmatter.ts`), and renders body via `WikiMarkdown`:

- `remark-gfm` — tables, task lists, strikethrough
- `remark-math` + `rehype-katex` — math
- `rehype-highlight` — fenced code blocks
- `remark-wikilink` — `[[Page Title]]` → `/wiki/:slug` (AST transform, not string rewrite)
- `@tailwindcss/typography` — prose styling

`fetchAllTitleSlugMap()` paginates wiki list (backend `page_size` cap 500) to resolve wikilinks.

---

## Configuration and secrets

| Variable | Purpose |
|----------|---------|
| `DATABASE_URL` | Async SQLAlchemy URL (`postgresql+psycopg://…`) |
| `MUNGER_CHECKPOINTER_URL` | LangGraph Postgres checkpointer (sync URL) |
| `DATA_DIR` | Root for sources, wiki exports, custom skills |
| `LLM_DEFAULT_PROVIDER` / `LLM_DEFAULT_MODEL` | Default LLM routing |
| `OPENROUTER_API_KEY`, etc. | Provider credentials |
| `MUNGER_WORKER_ID`, `MUNGER_WORKER_CONCURRENCY` | Worker identity and parallelism |
| `TEST_DATABASE_URL` | pytest only; must be `munger_test`, never `munger` |

Copy `munger/.env.example` → `munger/.env` for local Pigsty credentials.

---

## Development vs production URLs

| Surface | Dev (typical) | Docker Compose |
|---------|---------------|----------------|
| Frontend | `http://localhost:3000` (`npm run dev` in `app/`) | `http://localhost:13000` |
| Backend API | `http://localhost:18000` | `http://localhost:18000` |
| API docs | `http://localhost:18000/docs` | same |
| Postgres | Pigsty host `pigsty:5432` | same (via `docker_default`) |

During active frontend work, prefer Vite on **:3000** — the Docker frontend image may be stale relative to `app/src/`.

---

## Verification commands

```bash
# Frontend (from app/)
npm run build
npm run lint

# Backend (from munger/backend/, Postgres + munger_test required)
export TEST_DATABASE_URL=postgresql+psycopg://munger_app:…@localhost:5432/munger_test
pytest tests/ -v

# Full stack (from munger/)
docker compose up -d
```

---

## Intentional boundaries

| In scope | Out of scope (today) |
|----------|----------------------|
| Filesystem `SKILL.md` + ingest agent | DB workflow tables / `/api/workflows` |
| Five ingest tools, strict order | `{{step:…}}` SKILL execution |
| Postgres + Alembic | SQLite dev path |
| Polling-based ingest status | WebSocket push (not required for completion) |
| Wiki wikilinks `[[…]]` | `#tags`, `![[embed]]` |

---

## Further reading

- `munger/backend/WORKFLOW_ARCH.md` — skill format and ingest harness detail
- `munger/README.md` — Docker quick start and configuration
- `AGENTS.md` — repo conventions for contributors
