# Agent Smoke Checklist (AGENTS.md tree only)

Run with fresh agent context: load `AGENTS.md`, `app/AGENTS.md`, `munger/AGENTS.md`, `munger/backend/AGENTS.md` — **not** `ARCHITECTURE.md`.

## Questions and expected answers

| # | Question | Expected |
|---|----------|----------|
| 1 | Frontend dev URL? | `http://localhost:3000` |
| 2 | Docker frontend URL? | `http://localhost:13000` |
| 3 | Backend API URL? | `http://localhost:18000` |
| 4 | Test database? | `munger_test` via `TEST_DATABASE_URL`; never `munger` |
| 5 | Active ingest skill? | `default-ingest/SKILL.md` (`ingest`) |
| 6 | Other SKILL files? | 3 legacy/dormant, not executed |
| 7 | Wired frontend routes? | `/`, `/ingest`, `/wiki`, `/wiki/:slug` (4) |
| 8 | Analysis page wired? | No |
| 9 | SQLite current? | No — Postgres only |
| 10 | `/api/workflows` current? | No — removed |
| 11 | WebSocket for ingest status? | No — polling |

## Pass criterion

Agent answers Q1–Q8 correctly and does **not** cite SQLite, `/api/workflows`, or WebSocket as current architecture.

## Manual verification (2026-06-09)

Answers derivable from AGENTS.md tree alone: **PASS** (all rows match nested doc content).
