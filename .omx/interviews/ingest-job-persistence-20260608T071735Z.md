# Deep Interview Transcript: Ingest job persistence

**Profile:** Standard | **Rounds:** 4 | **Final ambiguity:** ~7% | **Threshold:** 20%

## Problem statement
Uploading a PDF on `/ingest` shows a job card, but navigating away and back clears the list. User cannot track uploads or see success/failure.

## Codebase evidence
- `app/src/pages/Ingest.tsx` stores jobs in `useState` only; unmount clears state.
- Backend persists sources; `GET /api/sources` and `GET /api/sources/{id}/status` exist.
- Ingestion continues server-side after navigation.

## Q&A

### R1 — Outcome: what should the queue show on return?
**Answer:** All sources from the backend (full history, newest first).

### R2 — Non-goals: what not to build?
**Answer:** Full queue UX — persistence, filters, delete, resume polling for in-progress jobs.

### R3 — Decision boundary: delete behavior?
**Answer:** Backend delete via existing API, with confirmation dialog.

### R4 — Pressure pass: pagination for large lists?
**Answer:** Paginated (e.g. 20 per page with Next/Prev).

## Clarity breakdown

| Dimension | Score |
|-----------|-------|
| Intent | 0.95 |
| Outcome | 0.95 |
| Scope | 0.95 |
| Constraints | 0.85 |
| Success criteria | 0.90 |
| Context (brownfield) | 0.95 |

**Weighted ambiguity:** ~7%

## Pressure-pass finding
"All backend sources" was stress-tested for scale; user chose paginated loading rather than loading everything at once.
