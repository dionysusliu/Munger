# RALPLAN: DeerFlow Agent Harness v2 for Munger Ingest

## Metadata
- **Source spec:** `.omc/specs/deep-dive-deerflow-agent-harness-architecture.md`
- **Trace:** `.omc/specs/deep-dive-trace-deerflow-agent-harness-architecture.md`
- **DeerFlow reference:** `~/Services/deerflow/backend/packages/harness/deerflow/`
- **Mode:** Consensus (--direct, skip interview)
- **Supersedes:** `.omx/plans/prd-backend-pipeline-runtime-v1.md` (ingest topology only)

## Requirements Summary

Replace Munger's fixed 5-node LangGraph ingest DAG with a DeerFlow-style agent harness:

1. **`create_agent` ingest lead agent** with Munger-specific prompt (DeerFlow `lead_agent/agent.py` factory structure)
2. **5 ingest tools** wrapping existing services (not imperative graph nodes)
3. **DeerFlow-format ingest SKILL.md** (progressive load, `allowed-tools`, order-enforcing prose)
4. **Middleware chain** — DanglingToolCall → ToolErrorHandling → LoopDetection → TokenUsage → IngestToolGating (progressive)
5. **PostgreSQL checkpointer** via Pigsty when configured; MemorySaver fallback for dev/CI
6. **Progressive tool gating** — SKILL + middleware expose only next allowed tool; direct `agent.ainvoke()` (no supervisor subgraph v1)
7. **API unchanged:** `POST /sources/{id}/ingest` → background `IngestRunner`

## RALPLAN-DR Summary

### Principles
1. **Infrastructure internalized, LLM for reasoning** — tools/middleware/checkpointer are code; SKILL is prompt-level guidance
2. **Brownfield reuse** — wrap `StorageService`, `LLMService`, `EntityService`, `WikiService`; no service rewrite
3. **Literal copy where ROI is high** — DeerFlow factory/middleware/checkpointer; not sandbox/subagents/config
4. **E2e is the gate** — provider harness must pass before deleting v1 graph
5. **Incremental spikes** — deps → tools → harness → agent → e2e

### Decision Drivers
1. User rejected "LangGraph as prompt pipeline" — wants DeerFlow harness semantics
2. Working e2e + API contract must not regress
3. Postgres available for production-grade checkpoint/resume
4. `langchain>=1.2` upgrade is prerequisite for `create_agent`

### Viable Options

| Option | Pros | Cons |
|--------|------|------|
| **A: Full harness migration (chosen)** | Aligns with DeerFlow; checkpoint/observability; extensible | Large dep upgrade; copy/adapt effort |
| **B: Tool wrappers + deterministic supervisor** | Lower risk; faster | Doesn't satisfy "LLM does routing" vision; still code-orchestrated |
| **C: Wire WorkflowEngine + SKILL DSL** | Parser exists | Wrong SKILL format; unwired; not `create_agent` |

**Invalidation:** B rejected — user chose hybrid `create_agent` + max factory copy. C rejected — canonical target is new lead agent, not WorkflowEngine.

## Acceptance Criteria

| # | Criterion | Verification |
|---|-----------|--------------|
| AC1 | `create_agent` ingest lead agent replaces `ingest_graph.py` | Code review: no fixed 5-node DAG on live path |
| AC2 | 5 ingest tools wrap existing services | Unit test with mocks |
| AC3 | `default-ingest/SKILL.md` in DeerFlow format with `allowed-tools` | File inspection |
| AC4 | PostgreSQL checkpointer persists thread state | Integration test: interrupt + resume |
| AC5 | Token usage + loop detection middleware log per run | Log assertion in unit/integration test |
| AC6 | Provider e2e green | `test_provider_gate.py` |
| AC7 | Harness PASS | `scripts/run_test_harness.py` |
| AC8 | Wiki link parity (deterministic `create_link`) | Compare e2e wiki links vs v1 baseline |
| AC9 | Latency ≤ 2× v1 baseline on e2e fixture | Timed e2e run |
| AC10 | API contract unchanged | `POST /sources/{id}/ingest` returns 202; status progression |
| AC11 | DB-primary tools | No ingest tool accepts `text`, `summary`, or `entities` from LLM args — `source_id` only |
| AC12 | Progressive gating | At step N, only tool N+1 visible in tool list (unit test) |
| AC13 | Re-ingest isolation | `thread_id = ingest-{source_id}-{run_nonce}` prevents stale checkpoint resume |
| AC14 | Checkpointer fallback | Postgres when `MUNGER_CHECKPOINTER_URL` set; MemorySaver/sqlite otherwise; dev boots without Pigsty |
| AC15 | Extract fatal parity | Empty extract → `fail_source`; no further tool calls (mirrors v1 `mark_failed`) |
| AC16 | LLMService adapter only | No raw `ChatOpenAI`; reasoning-model handling via `extract_assistant_message_text` |

## Implementation Steps

### Phase 0: Dependency Spike (blocker gate)
**Files:** `munger/backend/requirements.txt`, `munger/docker-compose.yml`

- Add: `langchain>=1.2.15`, `langchain-openai>=1.2.1`, `langgraph-checkpoint-postgres>=2.0`, `psycopg[binary]>=3.2`, `psycopg-pool>=3.2`
- Remove or reconcile `langchain-core>=0.3` pin (langchain 1.x bundles core)
- Add env: `MUNGER_CHECKPOINTER_URL=postgresql://dbuser_dba:DBUser.DBA@host.docker.internal:5432/postgres`
- Spike script: import `create_agent`, compile no-tool agent, verify in Docker build
- **Gate:** Docker build succeeds; spike script runs

### Phase 1: Harness Infrastructure Copy
**New package:** `munger/backend/app/runtime/harness/`

| Source (DeerFlow) | Target | Adaptation |
|-------------------|--------|------------|
| `agents/factory.py` | `harness/factory.py` | Munger middleware list; no sandbox |
| `agents/thread_state.py` | `harness/thread_state.py` | `MungerIngestState` fields: source_id, entities, wiki_page_ids |
| `agents/middlewares/dangling_tool_call_middleware.py` | `harness/middlewares/` | Copy-as-is |
| `agents/middlewares/tool_error_handling_middleware.py` | `harness/middlewares/` | Copy-as-is; always-on |
| `agents/middlewares/loop_detection_middleware.py` | `harness/middlewares/` | Inline defaults |
| `agents/middlewares/token_usage_middleware.py` | `harness/middlewares/` | Log to Python logger |
| **New:** `ingest_tool_gating_middleware.py` | `harness/middlewares/` | Progressive exposure: only next tool in sequence |
| `runtime/serialization.py` | `harness/serialization.py` | Copy-as-is |
| `runtime/checkpointer/` | `harness/checkpointer/` | Postgres provider; `MungerAppConfig.checkpointer_url` |

**Config shim:** `app/runtime/harness/config.py` — pydantic-settings fields: `checkpointer_url`, `model_name`, `max_agent_steps`

**Do NOT copy:** `config/*`, `sandbox/`, `subagents/`, `tools/builtins/`, DeerFlow `prompt.py` product text

### Phase 2: Ingest Tools
**New file:** `munger/backend/app/runtime/tools/ingest_tools.py`

```python
@tool
async def extract_source_text(source_id: int) -> str: ...  # reads file, writes Source.content_text

@tool
async def summarize_source(source_id: int) -> str: ...  # reads Source.content_text from DB

@tool
async def extract_entities_from_text(source_id: int) -> list: ...  # reads content_text from DB

@tool
async def create_wiki_pages(source_id: int) -> list[int]: ...  # reads text/summary/entities from DB

@tool
async def finalize_ingest(source_id: int) -> str: ...  # reads entity_count from DB
```

**DB-primary contract:** Public tool args are `source_id` only. Each tool loads prior outputs from `Source` / `EntityMention` via existing services — never from LLM-passed pipeline data.

- Extract logic from `nodes/extract_text.py`, `nodes/summarize.py`, etc. (unchanged service calls)
- Tools receive `RuntimeServices` via closure/factory: `build_ingest_tools(services) -> list[BaseTool]`
- `extract_source_text`: fatal empty → `fail_source`; gating middleware blocks further tools
- `create_wiki_pages`: deterministic `create_link` (parity with current `save_wiki_node`)

**Test:** `tests/unit/test_ingest_tools.py` — mock services, verify side effects

### Phase 3: SKILL Rewrite + Loader
**Files:**
- Rewrite `munger/backend/data/workflows/default-ingest/SKILL.md` → DeerFlow format
- New: `app/runtime/harness/skills/loader.py` (merge DeerFlow `skills/parser.py` + Munger paths)
- New: `app/runtime/harness/skills/tool_policy.py` (copy DeerFlow; enforce `allowed-tools`)

SKILL body must explicitly state tool call order and non-fatal failure policy.

Deprecate `{{step:...}}` parsing for ingest (keep `WorkflowParser` for future non-ingest workflows).

### Phase 4: Ingest Lead Agent
**New files:**
- `app/runtime/agents/ingest_lead_agent.py` — mirrors DeerFlow `lead_agent/agent.py` structure
- `app/runtime/agents/ingest_prompt.py` — Munger ingest system prompt (NOT DeerFlow product prompt)

```python
def make_ingest_lead_agent(services: RuntimeServices, checkpointer) -> CompiledGraph:
    tools = build_ingest_tools(services)
    skill = load_skill("ingest")
    middleware = build_munger_middleware_chain(services)
    return create_agent(
        model=wrap_llm_service(services.llm),
        tools=tools,
        middleware=middleware,
        system_prompt=build_ingest_prompt(skill),
        checkpointer=checkpointer,
    )
```

**LLM bridge:** Mandate `LLMService` → `BaseChatModel` adapter only. Must preserve `extract_assistant_message_text` for reasoning models. **No raw `ChatOpenAI`.**

**Tool order enforcement:** `IngestToolGatingMiddleware` progressively exposes only the next tool in sequence (extract → summarize → entities → wiki → finalize). SKILL prose + `tool_policy.filter_tools()` whitelist. Post-hoc rejection middleware is safety net only, not primary enforcement.

### Phase 5: Runner Replacement (no supervisor subgraph v1)
**Files:** `app/runtime/ingest_runner.py`, deprecate `app/runtime/graph/ingest_graph.py`

**v1:** `IngestRunner` invokes compiled `create_agent` directly — no wrapper `StateGraph`. Supervisor subgraph deferred until a second agent exists.

```python
async def run(self, source_id: int) -> IngestRunState:
    agent = make_ingest_lead_agent(services, checkpointer)
    run_nonce = uuid4().hex[:8]
    thread_id = f"ingest-{source_id}-{run_nonce}"
    config = {"configurable": {"thread_id": thread_id}}
    result = await agent.ainvoke(
        {"messages": [HumanMessage(f"Ingest source {source_id}")]},
        config,
    )
```

- **Re-ingest:** New `run_nonce` per trigger prevents stale checkpoint resume
- **Crash resume:** Explicit future API (`POST .../ingest/resume`); not automatic on re-trigger
- Delete `ingest_graph.py` and all `nodes/*.py` after parity

### Phase 6: Docker + Postgres Wiring
**Files:** `munger/docker-compose.yml`, `app/core/config.py`

- Add `MUNGER_CHECKPOINTER_URL` to backend service env
- `extra_hosts: ["host.docker.internal:host-gateway"]` if not present
- Init checkpoint tables on startup when Postgres configured (`checkpointer.setup()`)
- **Fallback:** `MUNGER_CHECKPOINTER_URL` unset → `MemorySaver` (dev/CI); log active backend at startup

### Phase 7: Verification
1. `pytest tests/unit/test_ingest_tools.py tests/unit/test_ingest_agent.py -v`
2. `pytest tests/integration/test_provider_gate.py -v` (provider lane)
3. `python scripts/run_test_harness.py` → PASS
4. Checkpoint test: kill mid-ingest, resume, verify `completed`
5. Latency benchmark vs v1 (capture baseline before migration; document in PR notes)
6. `tests/unit/test_llm_adapter.py` — reasoning-model message extraction
7. `tests/unit/test_ingest_tool_gating.py` — progressive tool exposure per step
8. Checkpoint test: interrupt after `summarize_source`, resume with same `thread_id`, assert `completed`

## Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| `langchain>=1.2` breaks existing imports | Phase 0 spike; pin exact versions after spike |
| LLM skips `extract_entities` tool | `IngestOrderMiddleware` + SKILL order + unit test for policy |
| Postgres unreachable from Docker | `host.docker.internal`; fallback env doc; health check on startup |
| LLMService ↔ LangChain adapter bugs | Adapter unit test; keep `extract_assistant_message_text` |
| Latency regression from agent overhead | Middleware only essential set; benchmark gate AC9 |
| DeerFlow copy drift | Copy with attribution header; minimal edits per file |

## Verification Steps

```bash
# Phase 0
cd munger && docker compose build munger-backend

# Phase 7
cd munger/backend
pytest tests/unit/test_ingest_tools.py tests/unit/test_ingest_agent.py -v
pytest tests/integration/test_provider_gate.py -v -m integration
docker compose run --rm munger-backend python scripts/run_test_harness.py
```

## ADR

### Decision
Adopt DeerFlow-style `create_agent` ingest lead agent with literal copy of factory/middleware/checkpointer infrastructure, Munger-native tools and prompt, PostgreSQL checkpointer, hybrid SKILL-enforced tool ordering.

### Drivers
- User architectural pivot from fixed-node LangGraph to agent harness
- Postgres availability for checkpoint/resume
- Working e2e must remain green

### Alternatives Considered
1. **Keep v1 fixed graph** — rejected (architectural misalignment)
2. **Deterministic code supervisor only** — rejected (user chose hybrid create_agent)
3. **Wire WorkflowEngine** — rejected (wrong execution model)

### Why Chosen
Maximizes DeerFlow harness fidelity while scoping to ingest-only, no sandbox. Tools preserve service layer investment. Hybrid routing balances DeerFlow semantics with e2e reliability.

### Consequences
- Significant dep upgrade and new `app/runtime/harness/` package
- v1 node files deleted after parity
- Two SKILL formats coexist (DeerFlow for ingest; Munger DSL for future workflows)
- Operational dependency on Pigsty Postgres for checkpoint (dev)

### Follow-ups
- Supervisor subgraph when second agent (e.g. research) is added
- Phase 3 compiler: Munger DSL → tool plans (deferred)
- Subagents for parallel wiki generation (deferred)
- Munger 12-dim pipeline on same harness (deferred)
- Explicit resume API for crash recovery

## Changelog (Architect + Critic revisions)
- Tools redesigned as DB-primary (`source_id` only)
- Progressive `IngestToolGatingMiddleware` replaces post-hoc order rejection
- Thread ID uses `run_nonce` per trigger
- Checkpointer Postgres with MemorySaver fallback
- Minimal middleware chain: DanglingToolCall → ToolErrorHandling → LoopDetection → TokenUsage → IngestToolGating
- LLMService adapter mandated; ChatOpenAI option removed
- Direct agent invoke; supervisor subgraph deferred
- AC11–AC16 added
