# Deep Interview Spec: Ingest job persistence

## Metadata
- **Profile:** Standard
- **Rounds:** 4
- **Final ambiguity:** ~7%
- **Threshold:** 20%
- **Context type:** Brownfield
- **Context snapshot:** `.omx/context/ingest-job-persistence-20260608T071735Z.md`

## Intent (why)
The user treats Ingest as a durable work queue. Ephemeral UI state makes uploads feel lost and hides whether ingestion succeeded or failed after navigation.

## Desired outcome
Returning to `/ingest` (or refreshing) shows a backend-backed queue of all uploaded sources with live status, filters, pagination, and safe delete — not an empty list.

## In scope
1. **Hydrate queue from backend on mount**
   - Call `GET /api/sources` (new `listSources()` in `app/src/lib/api.ts`).
   - Map backend `status` / `error_message` to existing UI status badges.
   - Newest first (matches backend default ordering).

2. **Resume polling for in-progress jobs**
   - On load, start polling any source where `status` ∉ `{completed, failed}`.
   - Continue polling after upload as today.

3. **Pagination**
   - 20 sources per page with Next/Prev (or equivalent).
   - Use backend `page` / `page_size` params.

4. **Filters**
   - Status filter (e.g. all / processing / completed / failed) via `status_filter` query param.
   - File type filter for PDF vs MD via `file_type` query param.
   - Optional search by filename/title (client-side on current page or backend if added later).

5. **Delete with confirmation**
   - "Remove" triggers confirm dialog.
   - On confirm: `DELETE /api/sources/{id}` (add API helper if missing).
   - Remove card from UI on success.

6. **Preserve existing upload flow**
   - Dropzone upload → trigger ingest → poll unchanged.
   - After upload, refresh list or prepend new source.

## Out of scope / non-goals
- Push notifications or toasts outside the Ingest page.
- New backend endpoints (use existing sources list/status/delete).
- URL clip / DOCX / TXT ingest UI.
- Munger analysis or wiki integration on the ingest queue.
- Auto-archive or TTL hiding of old completed jobs.

## Decision boundaries (OMX may decide without confirmation)
- Default page size: 20.
- Filter UI: simple dropdowns/tabs above the queue (match existing Munger styling).
- Poll interval: keep ~2s for in-progress jobs.
- After delete confirm: use existing backend delete semantics (DB + associated data per API).
- Map all non-terminal backend statuses to "processing" in UI (existing mapping).
- Show `error_message` and `recent_logs` in expanded card (existing pattern).

## Constraints
- Brownfield React app; minimal diff focused on `Ingest.tsx` + `api.ts`.
- Direct CORS calls to `http://localhost:18000`.
- No git commit unless user asks.

## Testable acceptance criteria
1. Upload a PDF on `/ingest` → card appears with processing state.
2. Navigate to `/wiki` or `/` → return to `/ingest` → **same source still visible** with current status.
3. Hard refresh browser on `/ingest` → source list still populated from backend.
4. While ingestion runs, status updates without staying on the page continuously (polling resumes on mount).
5. Completed job shows completed badge; failed job shows error message.
6. Status filter shows only matching sources; pagination works across multiple pages.
7. Delete → confirmation → source removed from backend and disappears from queue.
8. `npm run build` passes.

## Assumptions exposed
| Assumption | Resolution |
|------------|------------|
| Cards vanish because state is ephemeral | Confirmed in code |
| Backend retains sources after navigation | Confirmed; list API exists |
| User wants full history | Confirmed R1 |
| User wants filters + delete + polling | Confirmed R2–R3 |
| Large lists need pagination | Confirmed R4 (20/page) |

## Technical touchpoints
- `app/src/pages/Ingest.tsx` — hydrate, pagination, filters, delete confirm, resume polling
- `app/src/lib/api.ts` — `listSources()`, `deleteSource()`

## Residual risk
None significant; requirements are concrete and APIs exist. Provider-dependent ingest failures are out of scope for this UI fix.
