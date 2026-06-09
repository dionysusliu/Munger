# Context Snapshot: Ingest Realtime Progress

**Created:** 2026-06-08T16:25:00Z  
**Task slug:** ingest-realtime-progress

## Task statement
User wants the frontend to show realtime progress for each ingestion task, potentially by exposing agent thinking trails or backend logs.

## Desired outcome (stated)
- Understand what pipelines exist today (is ingestion all we have?)
- Frontend can see live progress per ingestion job
- Backend may need to expose agent thinking trails and/or structured logs

## Probable intent hypothesis
User experienced opaque long-running ingest (e.g., large PDF) where the UI felt frozen or uninformative. They want observability into what the agent is doing during ingest, not just a coarse status badge.

## Known facts / evidence

### Backend pipelines (not just ingest)
| Pipeline | API surface | Frontend wired? |
|----------|-------------|-----------------|
| **Ingest agent** (LangGraph lead agent + 5 tools) | `POST /api/sources/{id}/ingest`, `GET /api/sources/{id}/status` | Yes — `/ingest` |
| **Workflows** (SKILL.md sequential engine) | `POST /api/workflows/{id}/run`, `GET /api/workflows/runs/{run_id}` | No — trimmed from nav |
| **Munger analysis** | `POST /api/munger/analyze/{source_id}` | No |
| **Wiki / entities / search** | Read/query APIs | Partial — wiki only |

### Current ingest progress model
- Source `status` enum: `pending`, `extracting`, `summarizing`, `extracting_entities`, `creating_pages`, `analyzing`, `completed`, `failed`
- `IngestionLog` table stores sparse action strings; `GET /status` returns last 10 logs
- Agent run uses LangGraph checkpointer with `thread_id` but messages are **not** persisted to API
- `log_ingestion()` called mainly on finalize/failure — not per tool step
- No SSE/WebSocket; prior deep-interview spec deferred streaming for v1

### Frontend ingest UI today
- Polls `GET /api/sources/{id}/status` every 2s for in-flight jobs
- Shows badge (Pending/Processing/Completed/Failed) + expandable recent logs
- `Logs.tsx` exists but uses mock data; not in sidebar

## Constraints
- Brownfield FastAPI + SQLite + React frontend
- Ingest must stay responsive (prior bug: blocking PDF OCR froze API)
- Docker dev stack at localhost:18000 / :3000

## Unknowns / open questions
- Primary user pain: stuck detection vs agent transparency vs debugging failures?
- Scope: ingest only, or workflows/analysis runs too?
- Acceptable transport: enhanced polling vs SSE/WebSocket?
- How much agent "thinking" to expose (tool calls only vs full LLM reasoning)?
- Non-goals and decision boundaries not yet stated

## Likely codebase touchpoints
- `munger/backend/app/api/sources.py` — status endpoint
- `munger/backend/app/runtime/ingest_runner.py` — agent invocation
- `munger/backend/app/runtime/tools/ingest_tools.py` — stage transitions
- `munger/backend/app/runtime/db_helpers.py` — `log_ingestion`
- `munger/backend/app/models/log.py` — `IngestionLog`
- `app/src/pages/Ingest.tsx` — polling + job cards
- `app/src/lib/api.ts` — status types
