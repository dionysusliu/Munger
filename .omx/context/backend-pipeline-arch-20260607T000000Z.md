# Context Snapshot: backend-pipeline-arch

**Timestamp:** 2026-06-07T00:00:00Z  
**Task slug:** backend-pipeline-arch

## Task Statement

Architect Munger backend service around a DeerFlow-inspired LangGraph dynamic runtime. Build first pipeline: ingestion → LLM entity extraction → wiki generation only.

## Desired Outcome

A clean backend pipeline runtime (not ad-hoc `IngestService` orchestration) that can execute the minimal ingest path reliably, with architecture borrowed from DeerFlow's factory-per-run + middleware/state patterns.

## Stated Solution

- User has working provider env var (OpenRouter) already
- Focus backend architecture only
- Scope narrowed to single pipeline: ingest → entities → wiki
- Learn from DeerFlow (`~/Services/deerflow`) LangGraph dynamic runtime ideas
- Construct runtime + first pipeline on top

## Probable Intent Hypothesis

User wants to replace or supersede the current split-brain state (working `IngestService` vs unwired `WorkflowEngine`) with a proper graph-based runtime before adding more features. DeerFlow is the reference implementation for how to do dynamic pipeline assembly.

## Known Facts / Evidence

### Munger (brownfield)
- **Working path today:** `IngestService.ingest_source()` — extract text → summarize → entities → wiki → index (`app/services/ingest_service.py`)
- **Workflow system exists but disconnected:** Parser + sequential `WorkflowEngine`, 4 builtin SKILL.md workflows, API exists
- **No LangGraph** in requirements; `WORKFLOW_ARCH.md` describes DeerFlow inspiration as target, not implemented
- **Blocker from PLAN.md resolved by user claim:** OpenRouter API key now available in env
- `default-ingest` SKILL.md defines intended pipeline but `on_ingest` never auto-runs; ingest API bypasses workflow engine
- `WorkflowEngine` API runs without injected services (LLM/entity/wiki) — steps no-op

### DeerFlow (reference)
- Does NOT hand-build StateGraph; uses `create_agent()` compiled graph
- Dynamic pipeline = per-run factory (`make_lead_agent`) + middleware chain + typed state reducers
- SKILL.md = declarative data loaded progressively, not compiled graph nodes
- Worker pattern: background run, checkpointer, SSE stream bridge
- Key borrowable files: `agents/factory.py`, `runtime/runs/worker.py`, `agents/thread_state.py`, `skills/parser.py`

## Constraints (stated)
- Only ingestion → entity extract → wiki pipeline
- Nothing else (no Munger 12-dim, search, graph UI backend, etc.)
- DeerFlow as architectural reference

## Unknowns / Open Questions
- Replace `IngestService` entirely vs migrate gradually?
- True LangGraph `StateGraph` with explicit nodes vs DeerFlow's `create_agent` + middleware approach?
- Keep SKILL.md step DSL vs adopt DeerFlow's prompt-driven workflow-in-markdown?
- Checkpoint/streaming/HITL needed for v1?
- What to do with existing `WorkflowEngine` sequential implementation?

## Decision-Boundary Unknowns
- What OMX may decide without user confirmation (schema changes, delete legacy code, dependency adds)?
- Acceptable breaking changes to existing API contracts?

## Likely Codebase Touchpoints
- `munger/backend/app/services/ingest_service.py` (current working pipeline)
- `munger/backend/app/workflow/engine.py`, `parser.py`, `builtins.py`
- `munger/backend/app/api/sources.py` (ingest trigger)
- `munger/backend/data/workflows/default-ingest/SKILL.md`
- `munger/backend/WORKFLOW_ARCH.md`
- `munger/backend/requirements.txt` (add langgraph/langchain)
