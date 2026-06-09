# Context Snapshot: Ingest Pipeline Observability

**Created:** 2026-06-08T21:00:00Z  
**Slug:** `ingest-pipeline-observability`  
**Related:** `.omc/specs/deep-dive-enhance-ingestion-pipeline-provenance.md`, `.omx/plans/ralplan-enhance-ingestion-pipeline-provenance.md`

## Task Statement

Alongside the provenance-first ingestion pipeline infra, define observability for workflow/pipeline execution — at minimum basic execution logs, and evaluate whether advanced observability tools fit Munger's vanilla-agent + SKILL/tool harness design.

## Desired Outcome

Operators and developers can understand what an ingest run did, where it failed, and (for the 9-tool pipeline) per-step quality signals — without over-engineering observability for a single-node dev stack.

## Stated Solution

Expose basic pipeline execution logs; explore advanced observability (LangSmith, OpenTelemetry, Prometheus, etc.) for current architecture.

## Probable Intent Hypothesis

User is planning the ingestion pipeline upgrade and wants observability designed **with** the new tools — not bolted on later. Concern: 9-tool pipeline is longer, more LLM-heavy, and provenance-first implies auditability. May want UI-visible progress + debuggability when chunk/glean steps fail silently.

## Known Facts (codebase evidence)

| Layer | What exists today |
|-------|-------------------|
| **Timeline events** | `ingest_events` table (`IngestEvent`): `event_type` + JSONB `payload` (`ingest_event.py`) |
| **Event types** | `status_change`, `agent_message`, `tool_call`, `tool_result`, `error` (`ingest_runner.py:41-74`) |
| **Recording** | `record_ingest_event()` in `events.py`; called from `IngestRunner.astream_events` loop |
| **Coarse logs** | `ingestion_logs` table (`IngestionLog`): trigger/finalize actions |
| **Job queue** | `ingest_jobs` with `heartbeat_at`, `claimed_by`, stale detection |
| **API** | `GET /api/sources/{id}/status?since_id=&limit=` returns `events[]`, `recent_logs[]`, job info (`sources.py:363-428`) |
| **Frontend** | `Ingest.tsx` polls status, accumulates events, shows timeline |
| **No advanced stack** | No OpenTelemetry, Prometheus, LangSmith, or structured metrics in repo |

## Gaps vs upcoming 9-tool pipeline

- Tools do not emit structured step metrics (entities/chunk ratio, glean counts, chunk_id)
- Events are LangGraph/agent-stream derived, not first-class tool-level observability
- `finalize_ingest` quality metrics planned in ralplan but not yet in event schema
- No cross-run dashboards; Postgres-only event store
- Long `chunk_document` runs may need intra-tool progress (heartbeat exists at job level only)

## Constraints

- Postgres-only stack (Pigsty); no separate observability DB assumed
- Polling-based UI (no WebSocket today)
- Vanilla agent harness — observability should not require proprietary agent platforms
- Lightweight ops (dev/small deployment)

## Unknowns / Open Questions

- Primary consumer: developer debugging vs operator UI vs audit/compliance?
- Is existing `ingest_events` + polling enough with richer payloads?
- Should observability align with provenance chain (chunk-level audit trail)?
- Budget for external tools (LangSmith, Grafana Cloud) vs in-app Postgres events?
- Non-goals: full APM? distributed tracing across future multi-worker fleet?

## Decision-Boundary Unknowns

- What OMX may decide without user confirmation (event schema? log retention? OTel yes/no?)
- Minimum viable vs nice-to-have for v1 of 9-tool pipeline

## Likely Touchpoints

- `munger/backend/app/runtime/events.py`
- `munger/backend/app/runtime/ingest_runner.py`
- `munger/backend/app/runtime/tools/*.py` (per-tool metrics)
- `munger/backend/app/api/sources.py` (status API)
- `app/src/pages/Ingest.tsx` (timeline UI)
- `munger/backend/data/workflows/default-ingest/SKILL.md` (quality metrics section)
- Alembic if new `pipeline_run_metrics` table needed
