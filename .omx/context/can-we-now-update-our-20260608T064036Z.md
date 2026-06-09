# Context Snapshot: Frontend wiring for ingestion UI

## Task statement
Update the frontend to wire in the backend ingestion pipeline. Remove frontend components that are not implemented yet; keep only ingestion progress, wiki page view, and an entry point for ingestion. Support both Markdown and PDF inputs; for PDF extraction, use `liteparse` (Python lib).

## Desired outcome
A minimal, clear UI that:
1. Lets the user upload a Markdown or PDF source.
2. Triggers backend ingestion for the uploaded source.
3. Shows ingestion progress (pending/processing/completed/failed) and failure messages.
4. Shows created wiki content (wiki browsing + wiki page by slug).

## Stated solution (from user)
- Remove all frontend components not implemented yet.
- Keep ingestion tasks progress, wiki page, and ingestion entry.
- Support Markdown and PDF; for PDF use `liteparse`.

## Probable intent hypothesis
Avoid mock/demo-only UI. The user wants ingestion and wiki flows to become real end-to-end paths wired to backend endpoints, with minimal distraction from unfinished analysis/search/etc.

## Known facts / evidence

### Frontend (current)
- `app/src/App.tsx` routes include: `/ingest`, `/wiki`, `/wiki/:slug`, plus `/search`, `/entities`, `/graph`, `/analysis`, etc.
- `app/src/components/Sidebar.tsx` nav items include `Search`, `Entities`, `Graph`, `Analysis` in addition to `Wiki` and `Ingest`.
- `app/src/pages/Ingest.tsx` is currently **mock-driven**:
  - Ingest jobs are `INITIAL_JOBS` with hardcoded statuses and a demo “Re-ingest” that cycles UI state.
  - Drag/drop accepts `application/pdf`, `text/plain`, `text/markdown`, and `docx`.
  - There are no visible calls to `/api/sources/upload`, `/api/sources/{id}/ingest`, or `/api/sources/{id}/status` in the component logic.
- `app/src/pages/WikiBrowser.tsx` and `app/src/pages/WikiPage.tsx` use `WIKI_PAGES` mock arrays and render static data rather than fetching from backend.

### Backend (available ingestion + wiki APIs)
- Ingestion upload: `POST /api/sources/upload` (multipart `file`, optional `title`)
- Trigger ingestion: `POST /api/sources/{source_id}/ingest` (sets source `pending`, returns `202`)
- Progress: `GET /api/sources/{source_id}/status` returns `status`, `error_message`, and `recent_logs`
- Wiki list: `GET /api/wiki` supports pagination + optional filters (`page_type`, `search`)
- Wiki page by slug: `GET /api/wiki/slug/{slug}`
- Wiki page content exists in DB and is returned by the wiki endpoints.

## Constraints
- Frontend should remain simple and clear; remove or hide components that aren’t implemented.
- UI must handle both Markdown and PDF uploads.
- PDF parsing approach is requested: use `liteparse` (likely requires backend extraction change, not just UI wiring).

## Unknowns / open questions
- Which exact screens/navigation should remain after “remove all frontend components not implemented yet”:
  - Keep only `Ingest` + `Wiki` routes?
  - Keep `Dashboard` but hide its mock sections?
  - What to do with existing sidebar items for `/search`, `/entities`, `/graph`, `/analysis`?
- Does “liteparse for PDF” mean:
  - Backend must be updated to use `liteparse` for `pdf` extraction, or
  - It’s acceptable to rely on the current backend PDF extraction (which already advertises PDF support)?
- Should ingestion progress polling be implemented using `GET /status` polling (simpler) vs any other mechanism?

## Likely codebase touchpoints
- `app/src/pages/Ingest.tsx` (replace mock jobs with backend calls + polling)
- `app/src/pages/WikiBrowser.tsx` and `app/src/pages/WikiPage.tsx` (replace mock data with backend fetches)
- `app/src/components/Sidebar.tsx` and `app/src/App.tsx` (remove/hide unimplemented routes)
- Possibly backend `StorageService.extract_text()` to add `liteparse` PDF extraction.

## Decision-boundary unknowns
- Minimal UI scope: keep only `/ingest`, `/wiki`, `/wiki/:slug`?
- Liteparse requirement: frontend-only wiring vs backend extraction change required.

