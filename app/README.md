# Munger Frontend (`app/`)

React 19 + TypeScript + Vite SPA for the Munger knowledge base.

## Agent docs

- [`../AGENTS.md`](../AGENTS.md) — repo-wide agent router (auto-loaded in Cursor)
- [`AGENTS.md`](./AGENTS.md) — frontend routes, key files, verify commands
- [`../ARCHITECTURE.md`](../ARCHITECTURE.md) — full system architecture

## Quick start

```bash
npm install
npm run dev    # http://localhost:3000
```

Backend API default: `http://localhost:18000` (set `VITE_BACKEND_BASE_URL` if needed).

## Verify

```bash
npm run build
npm run lint
```
