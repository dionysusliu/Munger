# Deep Dive Trace: deerflow-agent-harness-architecture

## Observed Result

Munger's ingest pipeline was recently migrated to a fixed LangGraph DAG (`extract_text` → `summarize` → `extract_entities` → `save_wiki` → `finalize`) with hardcoded per-node LLM prompts in `LLMService`. The user rejects this as insufficient: they want DeerFlow's agent harness model — static graph topology + dynamic routing, lead agent/supervisor, middleware, tools, progressive Skills — where infrastructure is internalized and the LLM only does reasoning/decisions. User adjusted Lane 2 to prioritize **literal DeerFlow code copy** over pattern-only borrowing.

## Ranked Hypotheses

| Rank | Hypothesis | Confidence | Evidence Strength | Why it leads |
|------|------------|------------|-------------------|--------------|
| 1 | **Partial literal DeerFlow harness copy** (middleware + tools + skills loader + checkpointer) atop Munger's ingest domain, NOT wholesale `lead_agent`/sandbox transplant | High | Strong | Lane 2 module audit: MIT license, copyable utilities exist; `lead_agent/`, `subagents/`, `sandbox/`, `config/` are XL-effort forks. Lane 1 confirms Munger has zero tool/middleware/agent layer on live ingest path. |
| 2 | **Munger runtime is architecturally misaligned** with DeerFlow — fixed DAG nodes calling `LLMService` directly, `default-ingest/SKILL.md` unwired | High | Strong | Lane 1: `ingest_graph.py` hardcodes 6 nodes; no `@tool`, no `create_agent`, no progressive skill load. `WorkflowEngine` + SKILL parser exist but disconnected from `POST /sources/{id}/ingest`. |
| 3 | **Migration preserves API+e2e only with deterministic or tightly-constrained supervisor**; full DeerFlow `create_agent` LLM routing risks breaking provider e2e | Medium | Moderate | Lane 3: API boundary is thin (`IngestRunner.run`); persistence contracts stable. But LLM-chosen tool order is non-deterministic; Munger `{{step:...}}` SKILL format incompatible with DeerFlow skill loader without bridge. |

## Evidence Summary by Hypothesis

### Hypothesis 1 (Partial literal copy — recommended path)

- **Lane 2 FOR:** MIT license; Python 3.12 + LangGraph version alignment; Munger already mirrors DeerFlow SKILL frontmatter parsing in `workflow/parser.py`; low-coupling modules: `thread_state.py`, `dangling_tool_call_middleware.py`, `clarification_middleware.py`, `skills/parser.py`, `skills/tool_policy.py`, `runtime/serialization.py`, `runtime/checkpointer/`.
- **Lane 2 AGAINST:** Munger lacks `langchain>=1.2` (only `langchain-core>=0.3`); DeerFlow `config/*` (30 modules) is ambient/global; `lead_agent/` is 500+ line product prompt wired to gateway/sandbox; `subagents/` + `sandbox/` assume container execution.
- **ROI copy set:** Upgrade deps → copy generic middlewares + `thread_state` reducers → adapt `runtime/checkpointer` + `serialization` → build Munger-native ingest tools → single lead ingest agent with progressive `ingest` SKILL.md.

### Hypothesis 2 (Runtime misalignment)

- **Lane 1 FOR:** `ingest_graph.py` compiles fixed linear graph; nodes call `LLMService.summarize/extract_entities/generate_wiki_page` with inline prompts; no `app/runtime/tools/`; API calls bare `graph.ainvoke()` without RunManager/checkpointer; runtime omits SKILL steps (link suggestions, foreach).
- **Lane 1 AGAINST:** LangGraph adopted; `RuntimeServices` DI container exists; `WorkflowEngine` has declarative `llm_call` from SKILL templates (closer to DeerFlow); migration from `IngestService` already done with unit tests.

### Hypothesis 3 (Migration path)

- **Lane 3 FOR:** 5 nodes map cleanly to `@tool` wrappers over existing services; e2e asserts persistence (`EntityMention`, wiki pages, `Source.status=completed`) not graph internals; `IngestRunner` entrypoint swappable.
- **Lane 3 AGAINST:** DeerFlow supervisor is LLM `create_agent` (non-deterministic); two incompatible SKILL formats; 8 SKILL steps ≠ 5 graph nodes; v1 PRD explicitly chose linear graph; full harness port is greenfield.

## Evidence Against / Missing Evidence

- **Hypothesis 1:** No dependency spike run yet — `langchain>=1.2.15` compatibility with Munger's `langchain-core>=0.3` unverified in scratch venv.
- **Hypothesis 2:** PRD v4 may have deliberately chosen fixed graph as v1 stopgap — "misaligned" may mean "intermediate by design," not accidental.
- **Hypothesis 3:** Provider e2e was green with `qwen/qwen3.6-plus` at last verification, but migration spike (Spike A/B/C) not executed.

## Per-Lane Critical Unknowns

- **Lane 1 (Munger misalignment):** Is `app/runtime/` the intended v1 stopgap, or is `WorkflowEngine` + `default-ingest/SKILL.md` meant to become the DeerFlow harness? Both exist; only runtime is wired to ingest API.
- **Lane 2 (Literal DeerFlow copy — user-adjusted):** Does Munger v1 target `create_agent` conversational runtime, or stay on `StateGraph` step DSL with DeerFlow middleware/checkpointer borrowed around it?
- **Lane 3 (Migration path):** Which "supervisor" is intended — (A) deterministic tool-call sequence, (B) hybrid `create_agent` with ordered-tool prompt, or (C) full DeerFlow lead agent + subagents?

## Rebuttal Round

- **Best rebuttal to leader (partial copy):** User explicitly wants DeerFlow architecture including supervisor-subgraph topology and "LLM does reasoning." A partial copy that keeps deterministic `StateGraph` edges contradicts the user's stated vision of dynamic routing via supervisor LLM decisions.
- **Why leader held:** Trace evidence shows wholesale `lead_agent`/subagent/sandbox copy is XL-effort and wrong abstraction for sequential ingest. The user's DeerFlow description separates **control flow layer** (static LangGraph topology) from **reasoning layer** (LLM chooses edges/tools). Partial copy of harness infrastructure (middleware, tools, skills) + Munger-native ingest lead agent satisfies both the letter (harness internalization) and feasibility (e2e preservation). Dynamic routing can live in a single supervisor node without porting DeerFlow's chat product stack.

## Convergence / Separation Notes

- Lanes 1 and 2 **converge**: Munger live ingest path lacks DeerFlow harness layers; `WorkflowEngine`/SKILL stack is the latent alternative but also incomplete.
- Lanes 2 and 3 **converge**: Tool wrappers over existing services are the migration bridge; literal copy applies to **infrastructure modules**, not **product modules** (`lead_agent`, `subagents`).
- Lanes 1 and 3 **separate on risk**: Functional misalignment (missing link-suggestions step) is separate from architectural style misalignment (fixed nodes vs agent harness). E2e may pass without DeerFlow migration; user wants architectural alignment regardless.

## Most Likely Explanation

Munger is at an **intentional v1 shortcut** (fixed LangGraph DAG) that functionally works but **architecturally diverges** from DeerFlow's layered harness. The correct migration is a **selective literal copy** of DeerFlow infrastructure (middleware chain, skills progressive loader, tool registry, checkpointer, `thread_state` reducers) plus a **Munger-native ingest lead agent** that wraps existing services as tools. The supervisor should use `create_agent` for reasoning/tool-selection within a **static supervisor-subgraph topology**, with ingest SKILL.md as prompt-level capability injection (DeerFlow format), not as compiled graph nodes. Deterministic fallback ordering may be required initially to preserve provider e2e.

## Critical Unknown

**Supervisor execution model:** Does the user accept a phased migration where v2 starts with deterministic tool sequencing inside a `create_agent` harness (infrastructure correct, routing constrained), or insist on fully dynamic LLM routing from day one (higher e2e risk, requires DeerFlow-format ingest SKILL + tool policy)?

## Recommended Discriminating Probe

**Spike A → B → C sequence:**

1. **Spike A:** Wrap 5 nodes as `@tool` functions; single supervisor node calls tools in fixed order. Run unit tests. Validates tool layer without LLM routing risk.
2. **Spike B:** Run provider e2e against Spike A. Validates persistence contracts.
3. **Spike C:** Replace fixed-order supervisor with `create_agent` + DeerFlow-format ingest SKILL + `allowed_tools` whitelist. Run e2e 5×. Compare mention/wiki completion rate vs Spike B.

Outcome C≈B → proceed with dynamic routing. Outcome C<B → ship hybrid (tool policy enforces order, LLM handles within-step reasoning).
