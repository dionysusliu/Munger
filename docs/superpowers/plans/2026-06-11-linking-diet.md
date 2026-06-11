# Linking Diet Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development.

**Goal:** Kill the co-mention edge explosion (21,526 edges = 54% graph density on one 12-page paper), gate wiki generation off junk entities, and make LLM usage visible per pipeline stage.

**Diagnosis (live data):** `_augment_text_mentions` (mention_method=`link_text`) inflates mentions to ~69/chunk (extraction itself: ~14); `_link_by_co_mention` pairs ALL mentions per chunk with a ≥1-shared-chunk rule → near-complete graph; co_mention:extracted relationships = 21,526:342. Wiki stage = one LLM call per entity (282), no threshold. Worker logs died with the container — no LLM-call telemetry survives.

**Changes:**
1. **Co-mention diet** (`linking_service._link_by_co_mention`): pair only `mention_method='extract'` mentions (augmented `link_text` mentions keep provenance value but don't vote on relatedness); require `len(shared_chunks) >= settings.ingest_comention_min_chunks` (new, default **2** — one co-location is noise). Expected: 21.5k → hundreds.
2. **Wiki gate** (`nodes_cognify` n_wiki): entity pages only for `mention_count >= settings.ingest_wiki_min_mentions` (new, default **2**); source summary page unaffected. Existing tests that rely on 1-mention entities getting pages: override the knob to 1 in their Settings (deliberate behavior change, not assertion-weakening) + one new test asserting the default gate.
3. **LLM telemetry** (`LLMService` + `pipeline_events.pipeline_step`): `LLMService.stats = {"calls": int, "ms": int}` incremented in chat/chat_structured/embed_texts; `pipeline_step(..., llm=None)` snapshots before/after and injects `llm_calls`/`llm_ms` into the step metrics (call sites pass `services.llm`). Shows up in the new stage drawer automatically.

**Ground truth:** `_link_by_co_mention` quoted mechanics (all-mentions select, per-chunk all-pairs, min-shared=1, confidence 0.6, idempotent delete of link methods); augment writes `mention_method="link_text"`, reduce writes `"extract"`; `pipeline_step` is an async contextmanager yielding the metrics dict (duration added at exit). Baseline **181 passed, 4 deselected**.

## Tasks
1. Co-mention diet + `INGEST_COMENTION_MIN_CHUNKS` (config + .env.example) + tests (1-shared → no edge; 2-shared → edge; link_text excluded; existing characterization adjusted deliberately where counts change).
2. Wiki gate + `INGEST_WIKI_MIN_MENTIONS` (config + .env.example) + tests (default gates singletons; affected legacy tests pin the knob to 1).
3. LLM stats + pipeline_step injection + tests (fake llm stats delta lands in metrics; nodes pass services.llm).
4. Review (edge semantics regression risk: does any existing test/feature depend on dense co_mention edges — EdgeService weights, retrieval graph channel? confirm acceptable) + full suite + STATUS/memory + PR + auto-merge.
