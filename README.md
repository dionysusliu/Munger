# Munger

Automated knowledge base: ingest sources, extract entities, build an interconnected wiki with LLM-powered analysis.

## Documentation

| Audience | Start here |
|----------|------------|
| **Cursor agents** | [`AGENTS.md`](./AGENTS.md) → area `AGENTS.md` files |
| **Architecture** | [`ARCHITECTURE.md`](./ARCHITECTURE.md) |
| **Docker quick start** | [`munger/README.md`](./munger/README.md) |

## Repo layout

- `app/` — React frontend (dev: `npm run dev` → `:3000`)
- `munger/` — Docker Compose stack (API `:18000`, nginx UI `:13000`)

## Archived (do not implement from)

- [`PLAN.md`](./PLAN.md) — historical progress log
- [`SPEC.md`](./SPEC.md) — historical specification
