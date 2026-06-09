# Context Snapshot: Ingest pipeline hardening (txn, instructor, rename, deferred)

**Timestamp:** 2026-06-09T08:47:35Z  
**Task slug:** ingest-pipeline-hardening

## Task statement

Four workstreams for the ingestion pipeline:
1. Audit all SQL queries; minimize transactions per query/operation
2. Adopt Pydantic + Instructor for constrained LLM structured output
3. Rename `add` → `intake`; rename node files to `nodes_{phase}.py` (e.g. `nodes_intake.py`, not `intake_nodes.py`)
4. Finish deferred tasks from cognee-inspired refactor (ralph v2.2)

## Desired outcome

A production-hardened ingest pipeline: fewer DB round-trips, reliable structured LLM outputs, clearer naming, and completed backlog from prior refactor.

## Stated solution

- SQL txn consolidation across ingest services + graph nodes
- Instructor wired into extraction/glean/link adjudication paths (Pydantic schemas already exist in `app/schemas/extraction.py`)
- Terminology: `add` subgraph → `intake`; `add_nodes.py` → `nodes_intake.py`; `add.py` → `intake.py`
- Complete deferred: golden corpus tests, materialized view, deprecate agent gating, frontend timeline labels

## Probable intent hypothesis

User sees the ralph implementation as functionally landed but not production-polished — transaction churn (especially `LinkingService` opening 9 sessions, `map_chunk_service` per-chunk sessions) and hand-rolled JSON parsing are tech debt before scaling. Naming `add` was always ambiguous vs Cognee; `intake` matches Munger vocabulary.

## Known facts (brownfield evidence)

### SQL / transactions
- `linking_service.py`: **9** `async_session_maker()` contexts — text-mention loop opens session per match
- `map_chunk_service.py`: per-chunk session in `_wave_a_worker` + separate embed batch session; `map_single_chunk` similar
- `resolution_service.py`: single session for full reduce (good pattern)
- `chunk_service.py`: 3 session opens
- Graph nodes (`add_nodes.py`, `cognify_nodes.py`): multiple sessions per node
- `ingest_tools.py`: still exists for agent fallback path

### Instructor
- `instructor>=1.0.0` in requirements.txt but **not imported anywhere** in app code
- Extraction uses manual `_parse_json` + `ExtractionResult.model_validate` in `map_chunk_service.py`, `extraction_service.py`
- Pydantic schemas exist: `app/schemas/extraction.py` (`ExtractionResult`, `GleanResult`)

### Naming (current)
- `app/runtime/graphs/add.py`, `nodes/add_nodes.py`
- Parent graph: `graph.add_node("add", add_subgraph)` in `ingest.py`
- State: `AddState` in `state.py`
- Plan/spec still say `add` subgraph

### Deferred from ralplan v2.2 / ralph
| Item | Status |
|------|--------|
| Golden corpus `tests/fixtures/golden/` + `test_cross_chunk_golden.py` | Not created |
| `tests/fixtures/fake_llm.py` ScriptedLLMService | Not created |
| `entity_graph_edges` materialized view | Not created |
| Phase 9: remove `IngestToolGatingMiddleware` + legacy tool aliases | Not done |
| `app/src/pages/Ingest.tsx` timeline for new steps | Not updated |
| `munger/backend/AGENTS.md`, `WORKFLOW_ARCH.md` truth-up | Partial (ARCHITECTURE.md updated) |
| Resume + agent-fallback integration tests | Not created |
| `alembic upgrade head` for 004 on dev | Operator step |

### Tests today
- 29 unit tests pass (graph compile smoke, linking scoring, reduce prof merge)

## Constraints

- Brownfield — graph orchestration is default (`INGEST_ORCHESTRATOR=graph`)
- Postgres-only; no GDB
- User prefers `nodes_{phase}.py` naming convention

## Unknowns

- Priority order among 4 workstreams?
- SQL txn goal: per-node single txn, per-source single txn, or per-stage?
- Instructor: all LLM calls or extraction/glean only?
- Rename scope: API/events (`register_source` stays?) or only internal graph naming?
- Deferred tasks: all mandatory in one PR or phased?

## Decision-boundary unknowns

- May agent rename public step keys in `GRAPH_STEP_ORDER`?
- May remove agent path entirely in this slice?
- Breaking changes to `INGEST_ORCHESTRATOR` env values?

## Likely touchpoints

```
app/services/{linking_service,map_chunk_service,resolution_service,chunk_service,llm_service}.py
app/runtime/graphs/** (rename add→intake, nodes_*.py)
app/schemas/extraction.py
app/runtime/pipeline_events.py (step keys?)
tests/fixtures/golden/, tests/integration/
app/src/pages/Ingest.tsx
munger/backend/AGENTS.md, WORKFLOW_ARCH.md
alembic/versions/005_entity_graph_view.py (maybe)
```
