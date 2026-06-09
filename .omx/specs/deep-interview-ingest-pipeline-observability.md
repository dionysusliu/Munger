# Deep Interview Spec: ingest-pipeline-observability

**Slug:** `ingest-pipeline-observability`  
**Profile:** Standard  
**Rounds:** 6  
**Final ambiguity:** 12% (threshold 20%)  
**Type:** Brownfield  
**Context snapshot:** `.omx/context/ingest-pipeline-observability-20260608T210000Z.md`  
**Related:** `.omx/plans/ralplan-enhance-ingestion-pipeline-provenance.md` (ingest pipeline — observability ships as part of or alongside this work)

---

## Clarity Breakdown

| Dimension | Score | Gap |
|-----------|-------|-----|
| Intent Clarity | 0.90 | Clear — operator-facing visibility |
| Outcome Clarity | 0.90 | Step labels + metrics defined |
| Scope Clarity | 0.85 | Postgres-first; OTel schema only |
| Constraint Clarity | 0.90 | Polling + enriched API |
| Success Criteria | 0.80 | Concrete AC below |
| Context Clarity | 0.90 | Existing primitives mapped |

**Readiness gates:** Non-goals explicit (token/cost); decision boundaries delegated.

---

## Intent

Give **operators** (non-developers) trustworthy visibility into ingest pipeline execution on the Ingest page — what step is running, whether it succeeded, and meaningful per-step outcomes — without requiring log diving or understanding agent internals.

Observability should **compose with** the provenance-first 9-tool pipeline: step events become part of the same Postgres-backed audit story, not a separate proprietary stack.

---

## Desired Outcome

During and after an ingest run, the Ingest page shows:

1. **Human-readable pipeline progress** — e.g. "Extracting entities (step 3 of 9)"
2. **Per-step outcome metrics** — chunk count, entities extracted, glean additions, entities resolved, wiki pages created, links added
3. **Clear failure localization** — which step failed and operator-friendly error message
4. **No agent noise** — raw LLM agent messages hidden or collapsed by default (implementation detail)

Live updates via **existing 2s polling** on enriched `GET /api/sources/{id}/status`.

---

## In-Scope

### Backend — event model (Postgres-first)

Extend existing `ingest_events` + status API (do not replace):

| Event type | When | Payload (examples) |
|------------|------|---------------------|
| `pipeline_step_start` | Tool begins | `step_key`, `step_index`, `step_total`, `label`, `tool_name` |
| `pipeline_step_complete` | Tool succeeds | `step_key`, `duration_ms`, `metrics` (see below) |
| `pipeline_step_failed` | Tool errors | `step_key`, `message`, `recoverable` |
| `pipeline_summary` | finalize | `entities_per_chunk`, `chunk_count`, `entity_count`, `wiki_page_count` |

**Per-step `metrics` examples:**

| Step | Metrics |
|------|---------|
| `chunk_document` | `chunk_count`, `total_tokens` |
| `extract_entities_from_chunks` | `entities_raw`, `relationships_raw`, `chunks_processed` |
| `glean_entities` | `entities_added`, `glean_rounds` |
| `resolve_entities` | `entities_canonical`, `mentions_created`, `dedup_rate` |
| `generate_wiki_pages` | `pages_created`, `pages_updated` |
| `link_wiki_pages` | `links_created` |

**OTel-ready schema (v1 — fields only, no exporter):**

```json
{
  "trace_id": "optional-uuid",
  "span_id": "optional-uuid",
  "parent_span_id": null,
  "step_key": "extract_entities_from_chunks",
  "step_index": 3,
  "step_total": 9,
  "duration_ms": 12400,
  "metrics": { "entities_raw": 42, "chunks_processed": 8 }
}
```

Emit from tools (or thin shared `emit_pipeline_event()` helper) — implementation may choose pattern.

### Backend — enriched status API

Extend `GET /api/sources/{id}/status` response:

```json
{
  "current_step": { "key": "glean_entities", "label": "Refining entity extraction", "index": 4, "total": 9 },
  "step_metrics": { "chunk_count": 12, "entities_raw": 38 },
  "events": [ ... existing timeline ... ]
}
```

Denormalize `current_step` from latest events or `IngestJob` metadata for fast card render.

### Frontend — Ingest.tsx

- Replace raw `tool_call` / `agent_message` timeline as **primary** view with human step cards
- Show step progress (index/total) and per-step metrics on completion
- Keep expandable "technical detail" section optional (delegate layout)
- Map 9-tool pipeline steps to operator labels (delegate copy)

### Integration with provenance pipeline ralplan

Add observability tasks to ingest pipeline implementation (Phase 3–4):

- Each new tool emits `pipeline_step_*` events with metrics
- `finalize_ingest` emits `pipeline_summary` with quality ratios from SKILL
- Update `IN_FLIGHT_STATUSES` in `Ingest.tsx` for new source statuses (`chunking`, etc.)

---

## Out-of-Scope / Non-Goals

- **Per-step LLM token/cost tracking** (user confirmed)
- **OpenTelemetry exporter wired in v1** — schema-ready only
- **LangSmith / Langfuse / Prometheus / Grafana** in v1
- **WebSocket / SSE** — polling remains transport
- **Cross-run analytics dashboard** — per-source timeline only (unless trivially derived later)
- **Distributed tracing across multi-worker fleet** — future; design fields only
- **Provenance drill-down UI** — separate from this spec (backend provenance API may feed future UI)

---

## Decision Boundaries (OMX may decide)

- Event payload field names and Postgres retention policy
- Operator-facing step labels and Ingest.tsx layout
- OTel field naming conventions (`trace_id`, `span_id` placeholders)
- Whether metrics emit from each tool vs shared middleware wrapper
- Hiding/collapsing raw agent messages in UI
- Structured JSON logging to stdout (optional additive — not required unless useful for Docker ops)

---

## Constraints

1. **Reuse** `ingest_events`, `record_ingest_event()`, existing poll loop — extend, don't fork
2. **Postgres-only** event store for v1
3. **Vanilla harness** — observability must not require LangSmith or proprietary agent platforms
4. **Polling** — enrich API; no new real-time transport in v1
5. **Fail-safe** — event recording failures must not break ingest (existing `events.py` pattern)
6. **Payload size** — respect `MAX_PAYLOAD_CHARS` (4096); metrics should be compact numbers/keys

---

## Acceptance Criteria

- [ ] Each of the 9 ingest tools emits `pipeline_step_start` and `pipeline_step_complete` (or `pipeline_step_failed`) with `step_index`/`step_total`
- [ ] `pipeline_step_complete` includes step-specific `metrics` per table above
- [ ] `finalize_ingest` emits `pipeline_summary` with `entities_per_chunk` and counts
- [ ] `GET /api/sources/{id}/status` returns `current_step` and `step_metrics` for in-flight jobs
- [ ] `Ingest.tsx` shows human step label + progress (N/9) without requiring users to read `tool_call` events
- [ ] Failed ingest shows which `step_key` failed with readable error
- [ ] Event payloads include OTel-ready optional fields (`trace_id`, `span_id`, `duration_ms`) — exporter not required
- [ ] Existing `pytest` ingest tests pass; new unit tests for event emission per tool
- [ ] No token/cost fields in events or UI

---

## Assumptions Exposed

| Assumption | Resolution |
|------------|------------|
| Existing timeline is too technical for operators | Confirmed — replace primary view with step cards |
| `ingest_events` table is sufficient store | Yes for v1 |
| 2s polling is acceptable latency | User confirmed |
| Observability ships with 9-tool pipeline | Bundle with ralplan implementation |
| Operators don't need LLM message content | Implied by step_metrics choice; hide agent chatter |

---

## Pressure-Pass Findings

**Revisited:** Round 1 (operator UI) vs Round 2 (technical metrics).  
**Finding:** Step metrics (chunk counts, entity counts) serve operators only when wrapped in plain-language step labels — not raw JSON or snake_case tool names. UI must translate `extract_entities_from_chunks` → "Extracting entities".

---

## Technical Context

### Existing primitives (brownfield evidence)

```37:50:munger/backend/app/models/ingest_event.py
class IngestEvent(Base):
    event_type: Mapped[str]
    payload: Mapped[dict[str, Any]]
```

```363:428:munger/backend/app/api/sources.py
@router.get("/{source_id}/status")
# returns events[], recent_logs[], job info — supports since_id polling
```

```175:191:app/src/pages/Ingest.tsx
function formatEventText(event) {
  // raw tool_call / tool_result / agent_message text
}
```

### Recommended architecture (fits vanilla agent + SKILL harness)

```
Tool execution
    → emit_pipeline_event(step_start | step_complete | step_failed)
    → ingest_events (Postgres)
    → GET /status (denormalized current_step + step_metrics)
    → Ingest.tsx poll (2s)
```

**Why not LangSmith-first:** Harness is self-hosted LangGraph + Postgres; operator UI needs first-class API fields, not external trace UI. LangSmith optional later via same OTel fields.

**Why OTel-ready schema now:** 9-tool pipeline increases span count; future multi-worker or external APM benefits from consistent `step_key` / `duration_ms` / trace correlation without schema migration.

### Step label map (implementation default — delegable)

| `step_key` | Operator label |
|------------|----------------|
| `parse_document` | Reading document |
| `chunk_document` | Splitting into sections |
| `extract_entities_from_chunks` | Extracting entities |
| `glean_entities` | Refining extraction |
| `resolve_entities` | Matching entities |
| `summarize_source` | Writing summary |
| `generate_wiki_pages` | Creating wiki pages |
| `link_wiki_pages` | Linking pages |
| `finalize_ingest` | Finishing up |

---

## Relationship to Ingestion Pipeline Ralplan

**Recommendation:** Add **Phase 4b: Pipeline Observability** to `ralplan-enhance-ingestion-pipeline-provenance.md` or implement as a slice within Phases 3–4:

1. `app/runtime/pipeline_events.py` — shared emit helper with OTel-shaped payload
2. Wire into each tool module
3. Extend status API + Ingest.tsx
4. Tests: `test_pipeline_events.py`

No separate infra stack required — observability is an extension of existing `ingest_events`, not a new product.

---

## Interview Transcript

See `.omx/interviews/ingest-pipeline-observability-20260608T210500Z.md`
