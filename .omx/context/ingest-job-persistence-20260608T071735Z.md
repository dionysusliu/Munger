# Context Snapshot: Ingest job persistence across navigation

## Task statement
When uploading a PDF from the Ingest panel, a job card appears but disappears after navigating away and returning. The user cannot track uploaded work or see whether jobs succeeded or failed.

## Desired outcome
Ingest uploads remain visible and status remains knowable after leaving and returning to `/ingest` (and ideally across page refresh).

## Stated solution (what the user asked for)
Fix the ingest panel so uploaded jobs do not vanish on route change; user can track work and see success/failure.

## Probable intent hypothesis
The user treats Ingest as a durable work queue tied to backend ingestion, not a transient UI session. Losing cards feels like losing the upload itself.

## Known facts / evidence

### Frontend (current)
- `app/src/pages/Ingest.tsx` stores jobs in `useState<IngestJob[]>([])` only — no `localStorage`, no backend reload on mount.
- Navigating to `/wiki` or `/` unmounts `Ingest`; returning remounts with empty `jobs`.
- Polling uses `pollingRef` and stops on unmount (cleanup clears active polling).
- Upload flow: `uploadSource` → `triggerIngest` → poll `getIngestStatus` every ~2s until completed/failed.
- `app/src/lib/api.ts` has upload/trigger/status but **no** `listSources()` helper yet.

### Backend (available)
- `GET /api/sources` — paginated list with `status`, `error_message`, `filename`, `file_type`, timestamps.
- `GET /api/sources/{id}/status` — status + `recent_logs` for polling.
- Sources persist in DB; ingestion continues in background after navigation.

### Root cause (inferred)
Ephemeral React state + no hydration from backend on page load.

## Constraints
- Brownfield Munger app; keep UI simple and wired to existing backend APIs.
- Ingest panel currently supports PDF + Markdown only.

## Unknowns / open questions
- Should the queue show **all sources ever uploaded** or only **recent / active** jobs?
- Should persistence survive **browser refresh** or only **in-app navigation**?
- Should completed jobs stay in the list indefinitely or auto-archive after N days?
- Is local-only persistence (remember source IDs in `localStorage`) acceptable, or must the queue always reflect backend truth?

## Decision-boundary unknowns
- Scope of queue history (session vs all sources vs recent window).
- Whether OMX may choose backend-hydration-only vs localStorage hybrid without user confirmation.

## Likely codebase touchpoints
- `app/src/pages/Ingest.tsx` — hydrate jobs on mount, resume polling for in-progress sources
- `app/src/lib/api.ts` — add `listSources()` (+ optional filters)
