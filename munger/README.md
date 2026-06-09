# Munger — Automated Knowledge Base

> **Agents:** Read [`../AGENTS.md`](../AGENTS.md) and [`../ARCHITECTURE.md`](../ARCHITECTURE.md) first. This README is for human operators; some workflow/UI details below are simplified.

> *"Build a latticework of mental models, one source at a time."*

Munger is an automated knowledge base inspired by [Andrej Karpathy's LLM Wiki](https://github.com/karpathy/llm-wiki) concept and Charlie Munger's multi-dimensional thinking framework. It ingests source materials (PDFs, articles, web pages), extracts entities and concepts, and maintains an interconnected wiki through LLM-powered analysis.

![Munger Dashboard](https://o7liiwp2h7bb4.ok.kimi.link/screenshot.png)

---

## Table of Contents

- [Features](#features)
- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Quick Start (Docker Compose)](#quick-start-docker-compose)
- [Configuration](#configuration)
- [Workflow System](#workflow-system)
- [API Overview](#api-overview)
- [Development Guide](#development-guide)
- [Project Structure](#project-structure)
- [Troubleshooting](#troubleshooting)
- [License](#license)

---

## Features

### Core Capabilities

- **Source Ingestion** — Upload PDF, TXT, MD files or clip web URLs. Automatic text extraction and processing.
- **Entity Extraction** — LLM-powered identification of people, concepts, models, books, organizations, and more.
- **Wiki Generation** — Auto-generated interconnected wiki pages with internal linking (`[[Page Name]]` syntax).
- **Full-Text Search** — Search across all wiki pages, sources, and entities with relevance scoring.
- **Knowledge Graph** — Visual force-directed graph of wiki pages and their relationships.
- **Munger 12-Dimension Analysis** — Apply Charlie Munger's complete thinking framework to any source.

### Ingest agent (current runtime)

- **Active skill** — `default-ingest/SKILL.md` drives the LangGraph ingest worker (five tools, strict order).
- **SKILL.md files** — Live under `backend/data/workflows/`; see [`backend/WORKFLOW_ARCH.md`](./backend/WORKFLOW_ARCH.md).
- **Legacy files** — Three other SKILL.md files use old `{{step:…}}` syntax and are **not** executed by the worker.
- **12-dimension analysis** — `POST /api/munger/analyze/{source_id}` (not the Analysis UI page).

### LLM Provider Support

| Provider | Status | Notes |
|----------|--------|-------|
| **Kimi (Moonshot)** | Ready | `reasoning_content` support for K2 models |
| **OpenRouter** | Ready | Access to 200+ models via unified API |
| **OpenAI** | Ready | GPT-4o, GPT-4o-mini |
| **Anthropic** | Ready | Claude 3.5 Sonnet, Claude 3 Haiku |
| **Ollama** | Ready | Local models — Llama, Mistral, etc. |

---

## Architecture

```
                    Munger Architecture

  Frontend (React 19 + TypeScript + Tailwind CSS)
  ================================================
  /             /wiki        /search     /entities
  /ingest       /graph       /analysis   /settings
       |                      |
       +----------------------+
       |   REST API           |
       +----------------------+
  Backend (FastAPI + SQLAlchemy + Postgres)
  =========================================
  Sources API   Wiki API    Entities API   Search API
  Config API    Munger API
       |                      |
       +----------+-----------+
                  |
  +---------------v---------------+  +------------------+
  |   Ingest Agent Harness       |  |   LLM Service    |
  |  (SKILL.md + LangGraph)      |  |  + OpenRouter    |
  |  - Parser (SKILL.md)         |  |  + Kimi          |
  |  - Ingest tools + worker     |  |  + OpenAI        |
  |  - Checkpoint persistence    |  |  + Anthropic     |
  +---------------+---------------+  |  + Ollama        |
                  |                  +------------------+
  +---------------v---------------+
  |  Data Layer                   |
  |  - Postgres (Alembic)         |
  |  - File system (sources,      |
  |    wiki pages, SKILL.md)      |
  +-------------------------------+
```

---

## Prerequisites

### Required

- **Docker** >= 24.0
- **Docker Compose** >= 2.20
- **4GB RAM** minimum (8GB recommended)

### For Local LLM (Optional)

- **Ollama** installed on host or in Docker
- **8GB+ VRAM** for running 7B parameter models locally

### For Cloud LLM (Optional, choose one)

- **Kimi API Key** — [platform.moonshot.cn](https://platform.moonshot.cn)
- **OpenRouter API Key** — [openrouter.ai/keys](https://openrouter.ai/keys)
- **OpenAI API Key** — [platform.openai.com](https://platform.openai.com)
- **Anthropic API Key** — [console.anthropic.com](https://console.anthropic.com)

---

## Quick Start (Docker Compose)

### Step 1: Clone the Repository

```bash
git clone <repository-url> munger
cd munger
```

### Step 2: Configure Environment Variables

Create a `.env` file in the project root:

```bash
# Required: Choose your LLM provider
# Options: kimi, openrouter, openai, anthropic, ollama
LLM_DEFAULT_PROVIDER=kimi

# Required for cloud providers
# Choose at least one:
KIMI_API_KEY=your-kimi-api-key-here
# OPENROUTER_API_KEY=your-openrouter-api-key
# OPENAI_API_KEY=your-openai-api-key
# ANTHROPIC_API_KEY=your-anthropic-api-key

# Optional: Override default model
LLM_DEFAULT_MODEL=kimi-for-coding

# Optional: Ollama configuration (for local LLM)
OLLAMA_BASE_URL=http://host.docker.internal:11434

# Optional: Override ports
# BACKEND_PORT=18000
# FRONTEND_PORT=13000
```

### Step 3: Start Services

```bash
docker compose up -d
```

The first build will take 2-5 minutes. Subsequent starts are instant.

### Step 4: Verify Installation

```bash
# Check all containers are running
docker compose ps

# Check backend health
curl http://localhost:18000/api/health

# View logs
docker compose logs -f backend
docker compose logs -f frontend
```

### Step 5: Access Munger

| Service | URL | Description |
|---------|-----|-------------|
| Frontend (Docker) | [http://localhost:13000](http://localhost:13000) | nginx container |
| Frontend (dev) | [http://localhost:3000](http://localhost:3000) | Vite in `app/` (`npm run dev`) |
| API Docs | [http://localhost:18000/docs](http://localhost:18000/docs) | Interactive Swagger UI |
| Health | [http://localhost:18000/api/health](http://localhost:18000/api/health) | Health check endpoint |

### Step 6: Ingest Your First Source

1. Open [http://localhost:3000](http://localhost:3000) (Vite dev) or [http://localhost:13000](http://localhost:13000) (Docker UI)
2. Navigate to **Ingest** page
3. Upload a PDF, TXT, or MD file — or paste a URL
4. Trigger ingest — worker runs the `default-ingest` agent skill

### Step 7: Run Munger Analysis (API)

The **Analysis** page is not wired in the frontend router. Use the API:

```bash
curl -X POST http://localhost:18000/api/munger/analyze/{source_id}
```

---

## Configuration

### LLM Provider Configuration

Munger supports switching between LLM providers at any time. Configure via the **Settings** page or environment variables.

#### Kimi Code API — Recommended

```bash
LLM_DEFAULT_PROVIDER=kimi
KIMI_API_KEY=sk-your-key
KIMI_BASE_URL=https://api.kimi.com/coding/v1
LLM_DEFAULT_MODEL=kimi-for-coding
```

- Official third-party coding-agent endpoint
- OpenAI-compatible `/chat/completions` API
- Use the fixed model ID `kimi-for-coding`

#### OpenRouter

```bash
LLM_DEFAULT_PROVIDER=openrouter
OPENROUTER_API_KEY=sk-or-your-key
LLM_DEFAULT_MODEL=anthropic/claude-3.5-sonnet
```

- Access 200+ models through one API
- Pay-per-token with unified billing
- Good for comparing models

#### OpenAI

```bash
LLM_DEFAULT_PROVIDER=openai
OPENAI_API_KEY=sk-your-key
LLM_DEFAULT_MODEL=gpt-4o
```

#### Anthropic

```bash
LLM_DEFAULT_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-your-key
LLM_DEFAULT_MODEL=claude-3-5-sonnet-20241022
```

#### Ollama (Local)

```bash
LLM_DEFAULT_PROVIDER=ollama
OLLAMA_BASE_URL=http://host.docker.internal:11434
LLM_DEFAULT_MODEL=llama3.2
```

- Requires Ollama running on the host
- Free, private, no API keys needed
- Best models: `llama3.2`, `mistral`, `qwen2.5`

### Data Persistence

All data is persisted in Docker volumes:

| Volume | Path | Contents |
|--------|------|----------|
| `./data` | `/app/data` | Runtime data (sources, wiki exports, custom skills) |
| `./data/sources` | `/app/data/sources` | Uploaded source files |
| `./data/wiki` | `/app/data/wiki` | Generated wiki markdown files |
| `./data/workflows` | `/app/data/workflows` | Custom SKILL.md workflows |

**Backup:** Simply copy the `./data` directory.

### Custom SKILL.md files

Shipped skill source: `backend/data/workflows/`. Only `default-ingest` is executed by the ingest worker. Custom skills require harness integration — see [`backend/WORKFLOW_ARCH.md`](./backend/WORKFLOW_ARCH.md).

---

## Workflow System

Munger uses **filesystem SKILL.md** files with a **LangGraph ingest agent** (not the removed DB workflow engine).

| Skill | Status |
|-------|--------|
| `default-ingest/SKILL.md` | **Active** — worker loads on every ingest |
| `munger-12-dimension`, `quick-summary`, `entity-extract-only` | **Dormant** — legacy `{{step:…}}` format |

Full detail: [`backend/WORKFLOW_ARCH.md`](./backend/WORKFLOW_ARCH.md) and [`backend/AGENTS.md`](./backend/AGENTS.md).

---

## API Overview

### Core Endpoints

| Category | Endpoint | Description |
|----------|----------|-------------|
| **Sources** | `POST /api/sources/upload` | Upload a file |
| | `POST /api/sources/clip` | Clip a URL |
| | `GET /api/sources` | List sources |
| | `POST /api/sources/{id}/ingest` | Trigger ingestion |
| **Wiki** | `GET /api/wiki` | List wiki pages |
| | `GET /api/wiki/slug/{slug}` | Get page by slug |
| | `PUT /api/wiki/{id}` | Update page |
| **Entities** | `GET /api/entities` | List entities |
| | `GET /api/entities/{id}` | Get entity details |
| **Search** | `GET /api/search?q={query}` | Full-text search |
| | `GET /api/search/suggest?q={partial}` | Autocomplete |
| **Munger** | `POST /api/munger/analyze/{source_id}` | Run 12-dim analysis |
| | `GET /api/munger/dimensions` | List 12 dimensions |
| **Config** | `GET /api/config` | Get all config |
| | `PUT /api/config/{key}` | Update config |
| | `GET /api/config/models` | List available models |
| | `POST /api/config/test-model` | Test connection |
| **System** | `GET /api/health` | Health check |
| | `GET /api/stats` | System statistics |

Full interactive API documentation at `http://localhost:18000/docs`

---

## Development Guide

### Local Development (Without Docker)

#### Backend

```bash
cd backend

# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set environment variables
export DATABASE_URL=postgresql+psycopg://munger_app:password@localhost:5432/munger
export LLM_DEFAULT_PROVIDER=ollama
export LLM_DEFAULT_MODEL=llama3.2

# Run migrations (also runs on startup)
# Start server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### Frontend

```bash
# From the frontend build directory
cd ../frontend

# Note: The frontend is served via Nginx in production.
# For development, use the built React app from /mnt/agents/output/app
# Or build from source if you have the source files.
```

### Running Tests

Tests require a dedicated Postgres database (`munger_test`). Never point tests at the production `munger` database.

```bash
cd backend
export TEST_DATABASE_URL=postgresql+psycopg://munger_app:password@localhost:5432/munger_test
python scripts/bootstrap_test_postgres.py  # first-time setup
pytest tests/ -v
```

---

## Project Structure

```
munger/
├── README.md                          # This file
├── docker-compose.yml                 # Docker Compose configuration
├── start.sh                           # Quick start script
├── backend/                           # Python FastAPI backend
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── alembic.ini                    # Database migrations
│   ├── WORKFLOW_ARCH.md              # Workflow architecture doc
│   ├── app/
│   │   ├── main.py                    # FastAPI entry point
│   │   ├── core/
│   │   │   ├── config.py              # Application settings
│   │   │   └── database.py            # SQLAlchemy + Postgres
│   │   ├── api/                       # REST API routes
│   │   │   ├── router.py              # Route aggregator
│   │   │   ├── sources.py             # Source management
│   │   │   ├── wiki.py                # Wiki CRUD
│   │   │   ├── entities.py            # Entity management
│   │   │   ├── search.py              # Full-text search
│   │   │   ├── munger.py              # Munger 12-dim analysis
│   │   │   └── config.py              # System configuration
│   │   ├── models/                    # SQLAlchemy models
│   │   │   ├── source.py
│   │   │   ├── wiki.py
│   │   │   ├── entity.py
│   │   │   ├── munger.py
│   │   │   ├── log.py
│   │   │   └── config.py
│   │   ├── schemas/                   # Pydantic schemas
│   │   ├── services/                  # Business logic
│   │   │   ├── llm_service.py         # LLM provider abstraction
│   │   │   ├── storage_service.py     # File storage + text extraction
│   │   │   ├── ingest_service.py      # Ingestion pipeline
│   │   │   ├── entity_service.py      # Entity extraction + management
│   │   │   ├── wiki_service.py        # Wiki CRUD + cross-referencing
│   │   │   ├── munger_service.py      # 12-dimension analysis
│   │   │   └── search_service.py      # Full-text + semantic search
│   │   ├── runtime/                   # Ingest agent harness + SKILL.md loader
│   │   └── utils/
│   ├── alembic/                       # Database migrations
│   └── data/
│       ├── workflows/                 # Built-in + custom workflows
│       │   ├── default-ingest/SKILL.md
│       │   ├── munger-12-dimension/SKILL.md
│       │   ├── quick-summary/SKILL.md
│       │   └── entity-extract-only/SKILL.md
│       ├── sources/                   # Uploaded source files
│       ├── wiki/                      # Generated wiki pages
│       └── schema/
├── frontend/                          # React SPA (built)
│   ├── Dockerfile
│   └── nginx.conf
├── design/                            # Frontend design documents
│   ├── design.md
│   ├── dashboard.md
│   ├── wiki.md
│   ├── search.md
│   ├── entities.md
│   ├── ingest.md
│   ├── graph.md
│   ├── analysis.md
│   ├── logs.md
│   └── settings.md
└── .env                               # Environment variables
```

---

## Troubleshooting

### Container won't start

```bash
# Check logs
docker compose logs backend
docker compose logs frontend

# Rebuild from scratch
docker compose down -v
docker compose up --build -d
```

### LLM connection fails

```bash
# Test Kimi API
curl -H "Authorization: Bearer $KIMI_API_KEY" \
  https://api.kimi.com/coding/v1/models

# Test Ollama
curl http://localhost:11434/api/tags

# Via Munger API
curl -X POST http://localhost:18000/api/config/test-model \
  -H "Content-Type: application/json" \
  -d '{"provider":"kimi","model":"kimi-for-coding"}'
```

### Database issues

```bash
# Reset local data volume (WARNING: loses uploaded files!)
docker compose down -v
docker compose up -d
# Postgres data lives on Pigsty — reset via your DB admin tools if needed

# Or run migrations manually
docker compose exec backend alembic upgrade head
```

### Permission denied on data directory

```bash
# Fix permissions
sudo chown -R $(id -u):$(id -g) ./data
chmod -R 755 ./data
```

### Frontend shows blank page

```bash
# Check if backend is reachable
curl http://localhost:18000/api/health

# Check browser console for CORS errors
# CORS origins are configured in backend/app/core/config.py
```

---

## License

MIT License — see [LICENSE](LICENSE) file.

---

## Acknowledgments

- [Andrej Karpathy](https://github.com/karpathy) for the LLM Wiki concept
- [ByteDance DeerFlow](https://github.com/bytedance/deer-flow) for the workflow architecture inspiration
- [Charlie Munger](https://en.wikipedia.org/wiki/Charlie_Munger) for the mental models framework
