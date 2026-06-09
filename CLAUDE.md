# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Frontend (`app/`)
```bash
npm run dev       # Vite dev server → http://localhost:3000
npm run build     # Production build
npm run lint      # ESLint
```

### Backend (`munger/backend/`)
```bash
# Dev server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Tests (requires TEST_DATABASE_URL pointing to munger_test)
pytest tests/ -v
pytest tests/ -k "test_name" -v   # single test
pytest tests/unit/ -v              # unit only

# Migrations (auto-runs on startup)
alembic upgrade head
```

### Full Stack
```bash
cd munger
docker compose up -d
curl http://localhost:18000/api/health
```

## Architecture

Munger ingests source documents (PDF/URL/text), extracts entities and concepts via LLM, and builds an interconnected wiki. Two runtimes: FastAPI backend + async worker.

### Data Flow

```
Upload → POST /api/sources/{id}/ingest → IngestJob (DB queue)
  → Worker claims job → IngestRunner (LangGraph)
      intake subgraph:  register → parse → hash_dedup
      cognify subgraph: chunk → map (Send fan-out) → reduce_entities
                        → link → summarize → generate_wiki_pages → finalize
  → Wiki pages live, entity graph populated, searchable
```

### Backend Layers

**API** (`munger/backend/app/api/`) — FastAPI routes: `sources`, `wiki`, `entities`, `search`, `munger`, `config`, `health`

**Services** (`munger/backend/app/services/`) — Business logic:
- `LLMService` — multi-provider abstraction (OpenRouter/Kimi/OpenAI/Anthropic/Ollama); used for chat + embeddings
- `StorageService` — file upload, text extraction (PDF, web clip, docx, markdown)
- `WikiService` — wiki page CRUD, slug management, `[[wikilink]]` resolution
- `EntityService` — extraction, linking, mention provenance
- `SearchService` — full-text + semantic (pgvector, 768-dim qwen embeddings)
- `MungerService` — separate 12-dimension analysis (not part of ingest)
- `IngestJobService` — DB-backed job queue (no external broker)

**Runtime** (`munger/backend/app/runtime/`) — LangGraph ingest graphs + worker daemon. `default-ingest/SKILL.md` declares allowed tools and methodology loaded per job.

**Models** (`munger/backend/app/models/`) — SQLAlchemy ORM: `Source`, `Chunk`, `Entity`, `EntityMention`, `EntityRelationship`, `WikiPage`, `WikiLink`, `IngestJob`, `IngestEvent`, `MungerAnalysis`, `Config`

### Frontend

React 19 + Vite + Tailwind + shadcn/ui. HashRouter (static hosting compatible).

Active routes: `/` Dashboard, `/ingest`, `/wiki` list, `/wiki/:slug` reader.

Key files:
- `app/src/lib/api.ts` — typed fetch wrapper
- `app/src/lib/remark-wikilink.ts` — custom remark plugin transforms `[[Page]]` → `/wiki/:slug`
- `app/src/lib/wiki.ts` — slug map caching, wikilink resolution

### Database

Postgres only (no SQLite fallback). pgvector extension required. External Pigsty host in production. Alembic migrations run on API startup.

### LLM Configuration

| Env var | Default |
|---------|---------|
| `LLM_DEFAULT_PROVIDER` | `openrouter` |
| `LLM_DEFAULT_MODEL` | `deepseek/deepseek-v4-flash` |
| `LLM_EMBEDDING_MODEL` | `qwen/qwen3-embedding-8b` (768-dim) |

Copy `munger/.env.example` → `munger/.env` to configure.

### Testing

Tests require `TEST_DATABASE_URL` → `munger_test` DB. Conftest aborts if it detects the production DB. First-time setup: `python scripts/bootstrap_test_postgres.py`.

LangSmith tracing enabled via `LANGSMITH_TRACING=true` + `LANGSMITH_API_KEY`.

## Reference Docs

- `ARCHITECTURE.md` — system design, data model, API spec
- `AGENTS.md` — navigation tree, conventions, service ports
- `munger/backend/WORKFLOW_ARCH.md` — SKILL.md format, ingest runtime internals
- `PLAN.md`, `SPEC.md` — **archived**, historical only
