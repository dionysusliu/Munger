# Ralplan: Ingest Job Persistence (Revised v2)

**Source:** `.omx/specs/deep-interview-ingest-job-persistence.md`  
**Consensus:** Planner → Architect (CONCERNS) → Critic (ITERATE) → **Revised v2**

---

## RALPLAN-DR Summary

### Principles
1. **Backend is source of truth** — queue hydrates from `GET /api/sources`; React state is a view cache.
2. **Surgical brownfield diff** — only `app/src/lib/api.ts` + `app/src/pages/Ingest.tsx`; no new backend endpoints.
3. **Server pagination stays honest** — totals/page math reflect server filters except where explicitly documented as client-only.
4. **Polling is bounded** — poll only non-terminal jobs on the **current page**; cancel timers on page/filter/unmount.
5. **Vocabulary alignment** — status/file-type display maps from server values without silent mislabeling.

### Decision Drivers
1. Backend `status_filter` is exact-match; UI “processing” aggregates 5 DB statuses.
2. Polling + server-filtered lists can drift unless reconciled on terminal transitions.
3. `SourceResponse` frontend type is incomplete (`error_message` missing).

### Options Considered

| Option | Verdict |
|--------|---------|
| **A. Server-driven page + mapper** | ✅ **Chosen** — correct pagination, minimal diff |
| B. Client cache all sources | ❌ Rejected — breaks pagination at scale |
| **S1. Exact server status filters only** | ✅ Partial — All/Pending/Completed/Failed |
| **S2. Client-only “Processing” filter** | ✅ **Chosen as supplement** — no backend change; pagination hidden + banner when active |
| Backend `status IN (...)` for Processing | ❌ Deferred — requires backend change (out of scope) |

**Rejected alternative rationale:** Client-side filtering of entire dataset was rejected because user chose paginated full history (deep-interview R4).

---

## ADR

**Decision:** Server-driven ingest queue with hybrid status filtering.

**Drivers:** Existing APIs; no backend work; user wants full history + filters + delete.

**Alternatives considered:**
- Full client cache — rejected (pagination incorrect).
- Backend `phase=processing` filter — rejected (scope).
- Processing as server exact status — invalid (no such DB value).

**Why chosen:** Hydrate from `listSources`, exact filters where possible, client-only Processing mode with explicit UX caveat, bounded polling + refetch reconciliation.

**Consequences:**
- Processing filter shows active jobs from current fetched page only (banner explains).
- Delete cascades wiki pages server-side (existing API behavior).

**Follow-ups:** Backend `status_in` query param if Processing filter needs global pagination later.

---

## Implementation Steps

### Step 1 — API layer (`app/src/lib/api.ts`)
- Add `SourceListResponse { items, total, page, page_size }`.
- Extend `SourceResponse` with `error_message?: string | null`.
- Add `listSources({ page, page_size, file_type, status_filter })`.
- Add `deleteSource(id)` → `DELETE /api/sources/{id}` (no trailing slash).

### Step 2 — Mappers (`Ingest.tsx`)
- `sourceToJob(source: SourceResponse): IngestJob`
  - `fileType` from `source.file_type` → `PDF|MD|TXT|HTML|URL|FILE` (uppercase label)
  - `status` via existing `mapBackendStatus`
  - `error` from `source.error_message`
  - `size` from `source.file_size`
- Widen `IngestJob.fileType` to `string`.

### Step 3 — Server-driven state
- State: `page`, `total`, `statusFilter`, `fileTypeFilter`, `isLoading`, `listError`.
- `statusFilter`: `all | pending | processing | completed | failed`
- `fileTypeFilter`: `all | pdf | md`
- `fetchQueue()` calls `listSources` (page_size=20) unless Processing mode (see Step 4).
- `useEffect` refetch on mount + when `page`, filters change.

### Step 4 — Status filter behavior

| UI filter | API call | Display |
|-----------|----------|---------|
| All | no `status_filter` | all items |
| Pending | `status_filter=pending` | server page |
| Completed | `status_filter=completed` | server page |
| Failed | `status_filter=failed` | server page |
| **Processing** | no `status_filter`, `page_size=100` cap | **client-filter** to statuses in `PROCESSING_STATUSES` (exclude pending/completed/failed) |

Processing mode:
- Hide Prev/Next; show banner: “Showing in-progress jobs from recent sources.”
- Acceptable per scope (no backend change).

**Default filter:** `all` on mount.

**On upload:** reset to `all`, `page=1`, then refetch.

### Step 5 — Polling lifecycle
- Replace `pollingRef: Set<number>` with `pollTimers: Map<number, ReturnType<typeof setTimeout>>`.
- `pollStatus(id)`: clear existing timer for id; schedule 2s loop; store handle in map.
- `stopAllPolling()`: `clearTimeout` all handles; clear map.
- On page/filter change: `stopAllPolling()` then restart poll for visible non-terminal jobs.
- On unmount: `stopAllPolling()`.

### Step 6 — Reconciliation (filter drift)
- **Narrowing server filters** = Pending, Completed, Failed (not All, not Processing).
- When poll detects terminal transition (`completed`/`failed`) while narrowing filter active → debounced `fetchQueue()` (max once per 3s).
- All/Processing: in-place row update OK.

### Step 7 — UI controls
- Status dropdown + file-type dropdown above queue (Munger styling).
- Prev/Next when not in Processing mode; show “Page X of Y”.
- Loading spinner, list error banner, empty state preserved.

### Step 8 — Delete
- `window.confirm` with filename.
- `await deleteSource(id)` → `fetchQueue()`.
- If page > 1 and result empty → `page -= 1` then refetch.

### Step 9 — Upload flow (preserve)
- Keep dropzone → upload → trigger → poll.
- After batch: reset filters/page, refetch, start poll for new sources.

---

## Acceptance Criteria

1. Upload PDF → card shows; navigate away/back → same source visible with updated status.
2. Hard refresh → queue populated from backend.
3. In-progress job updates after returning to page (polling resumes).
4. Failed job shows `error_message` on hydrate (no extra poll required).
5. Filters: Completed/Failed/Pending use server totals; Processing shows in-progress subset with banner.
6. Pagination: >20 sources, Next/Prev correct when not in Processing mode.
7. Delete with confirm removes source; cancel keeps it; totals update.
8. `npm run build` passes.

---

## Verification Plan

| Check | Command / action |
|-------|------------------|
| Build | `cd app && npm run build` |
| Lint changed files | `cd app && npm run lint` (no new errors in touched files) |
| Manual AC 1–7 | against `http://localhost:18000` |
| Polling leak | DevTools: no status calls after leaving `/ingest` |
| Backend regression | `docker exec munger-backend pytest tests/test_sources_api.py -v` |

---

## File Touchpoints

- `app/src/lib/api.ts`
- `app/src/pages/Ingest.tsx`

---

## Execution Handoff

**Recommended:** `$ralph` — sequential, bounded scope, clear AC.

**Agent roster (if `$team`):**
- `executor` — api.ts + Ingest.tsx implementation
- `test-engineer` — manual AC script + build gate
- `verifier` — AC checklist sign-off

**Reasoning:** Sonnet for implementation; no Opus needed for this scope.

**Team verification path:** executor completes → verifier runs build + manual AC 1–7 → report.

**Launch hints:** `omx team start --spec .omx/plans/ralplan-ingest-job-persistence.md` (if using team mode).
