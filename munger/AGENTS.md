<!-- Parent: ../AGENTS.md -->

# Docker Stack Agent Guide (`munger/`)

Read [`../ARCHITECTURE.md`](../ARCHITECTURE.md) for system design. Backend detail: [`backend/AGENTS.md`](./backend/AGENTS.md).

## Services (`docker-compose.yml`)

| Container | Role |
|-----------|------|
| `munger-db-init` | One-shot Postgres bootstrap on Pigsty |
| `munger-backend` | FastAPI API (`:18000` → container `:8000`) |
| `munger-worker` | Ingest job worker (`python -m app.worker`) |
| `munger-frontend` | nginx SPA (`:13000` → `:80`) |

Postgres runs on **Pigsty** (external network `docker_default`), not inside this compose file.

## Ports (host)

| Service | Default host port | Container |
|---------|-------------------|-----------|
| Backend API | `18000` | `8000` |
| Frontend (Docker) | `13000` | `80` |

Frontend **dev** (Vite on host): `http://localhost:3000` from `app/` — not this compose service.

## Commands

```bash
cd munger
cp .env.example .env    # set Pigsty password + API keys
docker compose up -d
docker compose ps
docker compose logs -f munger-backend
docker compose logs -f munger-worker
```

Health check: `curl http://localhost:18000/api/health`

## Configuration

- `munger/.env` — local overrides (gitignored); see `.env.example`
- Never commit secrets
- `DATABASE_URL` → Postgres on Pigsty (`munger` database)
- `MUNGER_CHECKPOINTER_URL` → same Postgres for LangGraph checkpoints

## Data volumes

Bind mount `munger/data/` → `/app/data` in backend/worker:

| Host path | Contents |
|-----------|----------|
| `data/sources/` | Uploaded source files |
| `data/wiki/` | Wiki markdown **exports** (DB is source of truth for UI) |
| `data/schema/` | Schema artifacts |

Skill **source** lives in `munger/backend/data/workflows/` (baked into image as `/app/builtin-workflows`).

## Ingest (operator flow)

1. Upload via API or frontend Ingest page
2. `POST /api/sources/{id}/ingest` → 202 + `job_id`
3. Worker claims `ingest_jobs` row and runs LangGraph ingest agent
4. Poll `GET /api/sources/{id}/status` until `completed` or `failed`

## Munger 12-dimension analysis

Separate from ingest worker: `POST /api/munger/analyze/{source_id}`. No Analysis page in frontend router today.
