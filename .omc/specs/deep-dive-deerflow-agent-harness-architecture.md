# Deep Dive Spec: DeerFlow Agent Harness for Munger Ingest (v2)

## Metadata
- **Source:** deep-dive (trace + interview)
- **Slug:** deerflow-agent-harness-architecture
- **Profile:** Standard
- **Rounds:** 6
- **Final ambiguity:** 16%
- **Threshold:** 20%
- **Context type:** Brownfield
- **Trace artifact:** `.omc/specs/deep-dive-trace-deerflow-agent-harness-architecture.md`
- **DeerFlow reference:** `~/Services/deerflow/`
- **Prior v1 spec (superseded for ingest):** `.omx/plans/prd-backend-pipeline-runtime-v1.md`

## Goal

Refactor Munger's ingest pipeline from a **fixed LangGraph DAG with per-node LLM prompts** to a **DeerFlow-style agent harness** where:

- **Control flow layer:** Static LangGraph supervisor-subgraph topology (compiled at build time)
- **Reasoning layer:** `create_agent` lead ingest agent — LLM chooses tools within policy constraints
- **Capability injection layer:** Progressive DeerFlow-format `ingest` SKILL.md (not graph nodes)
- **Execution layer:** LangChain `@tool` wrappers over existing Munger services (Storage, LLM, Entity, Wiki)
- **Infrastructure layer:** Literally copied DeerFlow harness modules (middleware chain, factory, checkpointer, observability)

**Core principle:** Internalize agent infrastructure; LLM does reasoning/decisions only.

## Desired Outcome

`POST /api/sources/{id}/ingest` invokes a **Munger-native ingest lead agent** (DeerFlow `lead_agent/agent.py` factory structure) that:

1. Loads `ingest` SKILL.md progressively (DeerFlow format)
2. Calls ingest tools in **hybrid-enforced order** (SKILL + `allowed_tools` whitelist + tool policy)
3. Persists thread state to **PostgreSQL checkpointer** (Pigsty: `postgres://dbuser_dba:DBUser.DBA@localhost:5432/postgres`)
4. Runs observability middleware (token usage, loop detection, dangling tool-call repair)
5. Produces identical persistence contracts: `Source.status=completed`, entity mentions, wiki pages

The current `app/runtime/graph/ingest_graph.py` fixed-node graph is **replaced**, not extended.

## Constraints

### Architecture
- **Canonical target:** New `create_agent` ingest lead agent replaces `ingest_graph.py`; `WorkflowEngine` remains unwired for ingest
- **Supervisor model:** Hybrid — `create_agent` + ingest SKILL enforces tool order + `allowed_tools` whitelist; LLM reasons within steps
- **Literal copy scope:** Maximum practical — Tier 1+2 DeerFlow modules **plus** `lead_agent/agent.py` factory structure (Munger-specific system prompt, DeerFlow factory/middleware assembly code)
- **Dependency upgrade required:** `langchain>=1.2.15`, `langchain-openai>=1.2.1`, `langgraph-checkpoint-postgres`, `psycopg[binary]`, `psycopg-pool`
- **Checkpointer:** PostgreSQL via Pigsty Docker (`/Users/chuang/services/pigsty/docker`, port 5432); support hybrid store with Postgres plugins where DeerFlow pattern applies
- **Brownfield:** Reuse `EntityService`, `WikiService`, `LLMService`, `StorageService` as tool implementations
- **API contract unchanged:** `POST /sources/{id}/ingest` → 202, background execution, `Source.status` progression
- **Docker dev stack** must remain bootable; Munger backend connects to host Postgres for checkpointer (env-configured)

### Non-Goals (Explicit)
- Munger 12-dimension analysis pipeline
- Search-time dynamic workflow generation
- Frontend changes
- **Sandbox/bash execution** (DeerFlow sandbox stack not ported)
- Subagents/`task_tool` parallel delegation may be included if part of max-copy factory structure, but ingest remains sequential (no parallel entity wiki requirement)
- MCP/community tools (tavily, firecrawl, etc.) — Munger builtins only for v2

## Acceptance Criteria

1. **Unit tests:** Adapted `tests/unit/test_ingest_graph.py` → `test_ingest_agent.py` passes with mock services
2. **Provider e2e:** `tests/integration/test_provider_gate.py` green (`status=completed`, entity mentions, wiki pages)
3. **Harness:** `python scripts/run_test_harness.py` → Integration status: PASS
4. **Wiki link parity:** Canonical behavior = current runtime's deterministic `create_link` after entity pages (not LLM link-suggestions from old SKILL step 6)
5. **Latency:** Ingest on e2e fixture ≤ 2× current baseline
6. **Checkpoint/resume:** Ingest thread state persisted to PostgreSQL; interrupted run can resume from last tool call
7. **Observability:** Token usage + loop detection middleware wired and logging per ingest run
8. **SKILL format:** `default-ingest/SKILL.md` rewritten to DeerFlow format; `{{step:...}}` DSL deprecated for ingest
9. **Retirement:** `ingest_graph.py` + imperative node files removed or reduced to thin tool wrappers

## Technical Context

### Current State (Munger)
```
POST /sources/{id}/ingest → IngestRunner → StateGraph:
  extract_text → summarize → extract_entities → save_wiki → finalize
  (mark_failed on fatal extract)
```
- Nodes call `LLMService` with hardcoded prompts
- No `@tool`, no `create_agent`, no middleware, no progressive skills on live path
- `WorkflowEngine` + `default-ingest/SKILL.md` exist but unwired

### Target State (DeerFlow-inspired)
```
POST /sources/{id}/ingest → IngestRunner → LangGraph supervisor subgraph:
  lead_ingest_agent (create_agent)
    ├── middleware chain (DeerFlow-copied)
    ├── progressive ingest SKILL.md
    ├── tools: extract_source_text, summarize_source, extract_entities,
    │          create_wiki_pages, finalize_ingest
    └── PostgreSQL checkpointer (thread state)
```

### DeerFlow Literal Copy Map (v2)

| Module | Strategy | Notes |
|--------|----------|-------|
| `agents/lead_agent/agent.py` + `factory.py` | Copy structure, Munger prompt | Factory assembly pattern; not DeerFlow product prompt |
| `agents/thread_state.py` | Copy-with-adaptation | `MungerThreadState` schema for ingest |
| `agents/middlewares/*` (generic) | Copy-as-is / adapt | dangling_tool_call, loop_detection, token_usage, clarification, summarization, todo |
| `skills/parser.py`, `tool_policy.py`, `types.py` | Merge with `workflow/parser.py` | DeerFlow format becomes canonical for ingest |
| `runtime/checkpointer/` | Copy-with-adaptation | PostgreSQL provider; Pigsty connection |
| `runtime/serialization.py` | Copy-as-is | Message serialization |
| `runtime/runs/manager.py` | Copy-with-adaptation | Run lifecycle gaps vs current `IngestRunner` |
| `config/*`, `sandbox/`, `subagents/` | **Not copied** | Pattern reference only; out of scope |
| `tools/builtins/` | **Not copied** | Munger-native ingest tools instead |

### Tool Mapping (node → tool)

| Former node | Tool | Side effects (e2e-critical) |
|-------------|------|----------------------------|
| `extract_text` | `extract_source_text(source_id)` | `Source.content_text`; fatal → `failed` |
| `summarize` | `summarize_source(source_id, text)` | `Source.content_summary` |
| `extract_entities` | `extract_entities_from_text(source_id, text)` | **EntityMention rows** |
| `save_wiki` | `create_wiki_pages(source_id, text, summary, entities)` | Wiki pages + links |
| `finalize` | `finalize_ingest(source_id, entity_count)` | **`status=completed`** |

### Ingest SKILL.md (DeerFlow format — rewrite target)

```yaml
---
name: ingest
description: Process uploaded source into entities and wiki pages
allowed-tools:
  - extract_source_text
  - summarize_source
  - extract_entities_from_text
  - create_wiki_pages
  - finalize_ingest
---
```

Procedural markdown body: call tools in order; non-fatal failures on summarize/entities; fatal on empty extract.

### PostgreSQL (Pigsty)
- Connection: `postgres://dbuser_dba:DBUser.DBA@host.docker.internal:5432/postgres` (from Munger Docker)
- Env var: `MUNGER_CHECKPOINTER_URL` (or reuse DeerFlow-style config shim)
- Schema: LangGraph checkpoint tables via `langgraph-checkpoint-postgres`

## Assumptions Exposed

| Assumption | Resolution |
|------------|------------|
| Full DeerFlow `lead_agent` prompt is needed | **Rejected** — copy factory structure only; Munger-specific ingest prompt |
| Dynamic LLM routing from day one | **Rejected** — hybrid order enforcement via SKILL + tool policy |
| Munger `{{step:...}}` DSL continues for ingest | **Rejected** — rewrite to DeerFlow SKILL format |
| SQLite checkpointer sufficient | **Rejected** — user deployed Postgres; use `langgraph-checkpoint-postgres` |
| Sandbox needed for ingest | **Rejected** — explicit non-goal |
| `WorkflowEngine` becomes harness | **Rejected** — `create_agent` lead agent is canonical |
| Wholesale DeerFlow transplant | **Rejected** — max copy = factory + infrastructure; not sandbox/config/subagents product stack |

## Ontology

| Entity | Definition | Stability |
|--------|------------|-----------|
| **Ingest Lead Agent** | `create_agent` instance with ingest tools, middleware, progressive SKILL | Stable |
| **Ingest Tool** | LangChain `@tool` wrapping existing Munger service method | Stable |
| **Ingest SKILL** | DeerFlow-format markdown capability injection (not graph node) | Stable |
| **Thread State** | LangGraph checkpointed state per ingest run (PostgreSQL) | Stable |
| **Supervisor Subgraph** | Static LangGraph topology hosting lead agent node | Stable |
| **Middleware** | Cross-cutting harness concern (AOP between agent turns) | Stable |
| **Runtime Graph (v1)** | Fixed 5-node DAG | **Deprecated** |

## Ontology Convergence

- Started with ambiguous "DeerFlow architecture" — converged to **4-layer model** (control flow / reasoning / capability injection / execution)
- "Graph node per LLM call" → **tool per side effect, SKILL per methodology**
- "Copy DeerFlow" → **max literal copy of factory/infrastructure, Munger-native domain tools/prompt**
- "Supervisor" → **hybrid `create_agent` with order-enforcing SKILL**, not deterministic code-only nor fully dynamic

## Trace Findings

**Most likely explanation:** Munger v1 fixed LangGraph was an intentional shortcut that functionally works but architecturally diverges from DeerFlow. Migration path is selective literal copy of harness infrastructure + Munger-native ingest lead agent.

**Per-lane unknowns resolved:**
1. Canonical target → `create_agent` lead agent replaces runtime graph
2. Literal copy → max copy (factory + infrastructure tiers)
3. Supervisor → hybrid SKILL-enforced ordering

**Evidence shaping interview:**
- Two parallel ingest stacks (runtime vs WorkflowEngine) — runtime was live but wrong architecture
- DeerFlow `lead_agent`/sandbox/subagents not portable wholesale; factory/middleware/checkpointer are
- E2e preservation requires hybrid routing, not full dynamic LLM tool selection
- Postgres available for production-grade checkpoint/resume

## Interview Transcript

| Round | Dimension | Question | Answer |
|-------|-----------|----------|--------|
| 1 | Goal | Canonical execution target? | **A** — New `create_agent` ingest lead agent replaces runtime graph |
| 2 | Constraints | Supervisor execution model? | **B** — Hybrid: `create_agent` + SKILL enforces order + `allowed_tools` |
| 3 | Constraints | Literal DeerFlow copy bundle? | **D** — Maximum copy including `lead_agent` factory structure |
| 4 | Criteria | Ingest SKILL format? | **A** — Rewrite `default-ingest` to DeerFlow SKILL format |
| 5 | Criteria | Acceptance gates? | **Full harness** — e2e + parity + latency ≤2× + checkpoint + observability; Postgres via Pigsty |
| 6 | Constraints | Non-goals? | **B** — Ingest only + no sandbox/bash |

**Ambiguity progression:** 100% → 64% → 45% → 32% → 22% → 18% → **16%**

## Implementation Phases (Suggested)

### Phase 0: Dependency spike
- Add `langchain>=1.2.15`, `langchain-openai`, `langgraph-checkpoint-postgres`, `psycopg`
- Verify `create_agent` imports in Munger backend container

### Phase 1: Infrastructure copy
- Copy DeerFlow factory/middleware/thread_state/checkpointer/serialization into `app/runtime/harness/`
- Adapt config shim: `MungerAppConfig` with checkpointer URL, model settings
- Wire PostgreSQL checkpointer to Pigsty

### Phase 2: Tools + SKILL
- Create `app/runtime/tools/ingest_tools.py` (5 tools wrapping existing services)
- Rewrite `data/workflows/default-ingest/SKILL.md` to DeerFlow format
- Implement progressive skill loader (merge DeerFlow `skills/` with Munger paths)

### Phase 3: Lead agent + graph
- `app/runtime/agents/ingest_lead_agent.py` — DeerFlow factory structure, Munger prompt
- Replace `build_ingest_graph()` with supervisor subgraph hosting `create_agent`
- Update `IngestRunner` for checkpointed `graph.ainvoke()` / resume

### Phase 4: Verification
- Spike A→B→C from trace (unit → e2e → dynamic comparison)
- Remove deprecated node files after parity confirmed

## Execution Bridge

Spec ready at: `.omc/specs/deep-dive-deerflow-agent-harness-architecture.md`

Recommended path: **Ralplan → Autopilot** (consensus-refine this spec, then execute)
