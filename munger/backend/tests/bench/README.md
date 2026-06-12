# Pipeline Bench

Repeatable benchmarks for the ingest pipeline. Two tiers share one synthetic
corpus (`corpus.py`, seed=7: a ~5 500-token systems paper with 30 embedded
entities) and one report shape, so any pipeline change gets an automatic A/B:

| Tier | File | LLM | Purpose |
|------|------|-----|---------|
| deterministic | `test_bench_pipeline.py` | `BenchScriptedLLMService` (canned) | CI regression bounds: co-mention diet, wiki gate, step telemetry |
| live | `test_bench_live.py` | real OpenRouter (`deepseek/deepseek-v4-flash`) | cost/latency truth: real `llm_calls`/`llm_ms` per step, baseline A/B |

Both tiers are marked `bench`, which `pytest.ini`'s
`addopts = -m "not integration and not bench"` deselects from the default
suite — they only run when you ask for them.

## Running the deterministic tier

Free, no network, scripted LLM, real Postgres writes. Requires the project
venv (system Python lacks the deps) and the dedicated test DB:

```bash
cd munger/backend
TEST_DATABASE_URL=postgresql+psycopg://munger_app:Munger.App.2026@localhost:5432/munger_test \
.venv/bin/python -m pytest tests/bench/test_bench_pipeline.py -o addopts="" -m bench -q -p no:cacheprovider
```

(`-o addopts=""` clears the default `not bench` exclusion; then `-m bench`
selects the tier.)

## Running the live tier — RETIRED (2026-06-12)

**The live tier is retired by policy: no long-running benchmarks, period.**
Provider-side latency floors (~55-60 s per structured call) and routing
instability (intermittent 403s, trickling responses) made every full run a
budget kill. The code stays as an A/B harness for the day a stable fast
extraction model exists, but it is NOT part of any workflow — do not run it
unattended, and never without the watchdog below. Real-pipeline cost/latency
truth now comes from the OTel stack on the live containers instead
(`docs/OBSERVABILITY.md`): every ingest gets per-step spans and per-call POST
spans for free.

### (Historical) how it was run

Same command plus a real key — **this spends money** (one full ingest is
~100–250 chat/embed calls against OpenRouter; small corpus, but wiki-page
generation is one call per entity mention):

```bash
cd munger/backend
OPENROUTER_API_KEY=sk-or-... \
TEST_DATABASE_URL=postgresql+psycopg://munger_app:Munger.App.2026@localhost:5432/munger_test \
.venv/bin/python -m pytest tests/bench/test_bench_live.py -o addopts="" -m "bench and live_llm" -v -p no:cacheprovider
```

* Without `OPENROUTER_API_KEY` the test **skips cleanly** (same opt-in
  mechanism as `tests/live/test_live_llm.py`).
* Model overrides: `LIVE_CHAT_MODEL` (default `deepseek/deepseek-v4-flash`),
  `LIVE_EMBED_MODEL` (default `qwen/qwen3-embedding-8b`; must produce 768 dims
  to match the `Vector(768)` columns).
* Transient provider errors (rate limit, timeout, connection) **skip** rather
  than fail.
* Expect minutes of wall time: wiki-page generation runs serially against the
  real model.

### Budget + realtime monitoring (don't babysit, don't let it run away)

**Hard rules:** kill a live run after **60 s with no observable progress**
(no new Tempo span, no new `pipeline_step_complete` row, no chunk
`map_status` transition), and never let one run past **10 minutes** total.
Per-call transport timeouts are 120 s and the map stage retries up to
`INGEST_MAP_MAX_WAVES=3` waves, so an unsupervised run can legally burn
~an hour — enforce both budgets OUTSIDE pytest:

```bash
( OPENROUTER_API_KEY=... TEST_DATABASE_URL=... \
  OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318 \
  .venv/bin/python -m pytest tests/bench/test_bench_live.py -o addopts="" \
    -m "bench and live_llm" -v -p no:cacheprovider & ); \
P=$!; sleep 600; kill $P 2>/dev/null   # hard cap; pair with the 60s probe below
```

Progress probe (run it every ~60 s; two identical results in a row = stalled,
kill the run):

```bash
curl -s 'http://localhost:3200/api/search?q=\{name="POST"\}&limit=5' | jq '.traces | length'
```

**Known latency floor (2026-06-12):** one `chat_structured` extraction call
against `deepseek/deepseek-v4-flash` measures **~55-60 s** — and stays there
even after the output-budget prompt halved the JSON payload (10.4k → 4.7k
chars), i.e. the floor is provider-side (hidden reasoning / routing), not
decode length. Best full live run (concurrency 5, output budgets, 60 s
transport bound): map of 10 chunks ≈ **5 min**, then reduce + wiki overran the
10-min budget → killed. The committed baseline is therefore DEFERRED until a
stable fast extraction model is picked (`LLM_EXTRACTION_MODEL` override is
ready; candidates measured 54-75 s or 403'd via OpenRouter on 2026-06-12).
Until then expect budget kills, not completions — that is the policy working,
not a bug.

With `OTEL_EXPORTER_OTLP_ENDPOINT` set (the compose LGTM stack exposes
`http://localhost:4318`), the bench process exports as service
`munger-bench-live`: every `ingest.step` span AND every OpenRouter HTTP call
(httpx auto-instrumentation) streams to Tempo within ~5 s. Watch progress live:

```bash
# step + LLM-call spans from the bench, last 15 min
curl -s 'http://localhost:3200/api/search?q=\{resource.service.name="munger-bench-live"\}&limit=20' | jq '.traces[].rootTraceName'
```

See `docs/OBSERVABILITY.md` for the full recipe set. A run that shows stalled
or pathologically slow provider calls in Tempo should be killed at the budget,
not waited out.

## Reports

Each run writes JSON into `tests/bench/reports/` (gitignored):

* deterministic → `reports/bench-deterministic.json`
* live → `reports/bench-live-<git-sha>.json`

Field meanings:

| Field | Meaning |
|-------|---------|
| `corpus_chars` | Length of the synthetic document |
| `chunks` / `windows` | Chunk count and extraction-window count (window = `INGEST_EXTRACTION_WINDOW_CHUNKS` consecutive chunks) |
| `entity_count` | Distinct entities with a mention for the benched source |
| `co_mention_count` | `co_mention` relationships created (the "diet" under test: must stay ≲ linear in entities, never all-pairs) |
| `wiki_pages` | Entities that got a wiki page (mention gate passed) |
| `singleton_count` | Entities below `INGEST_WIKI_MIN_MENTIONS` (must have **no** page) |
| `extract_calls` | Window-extraction calls (`chat_structured` with `ExtractionResult`) |
| `total_llm_calls` / `total_llm_ms` | Whole-run LLM totals (`total_llm_ms` live tier only; scripted calls report 0 ms) |
| `steps.<key>` | Per pipeline step: `duration_ms` (wall), `llm_calls`, `llm_ms` (from `LLMService.stats` snapshots in `pipeline_step`) |
| `meta` | Live tier only: tier, git sha, models, wall time, timestamp |

## Baseline A/B (live tier)

`tests/bench/baselines/baseline.json` is a **committed** live report — the
reference for "what the pipeline costs today". When it exists, every live run
compares per-step `duration_ms` and `llm_calls` against it.

**Policy: warn, never fail.** Live latency is inherently noisy and a red CI
from provider weather helps nobody. A regression emits a
`BenchBaselineWarning` (visible in pytest's warnings summary) when:

* a step's `duration_ms` exceeds **2×** baseline — only checked for steps with
  a baseline duration ≥ 100 ms (sub-100 ms steps are scheduler noise), or
* a step's `llm_calls` exceeds **1.5×** baseline (a >50% call-count increase —
  this one is deterministic-ish and usually means a code change added calls).

Treat warnings as a prompt to investigate, not a verdict.

### Refreshing the baseline

When a pipeline change *intentionally* shifts cost/latency (or models change):

```bash
# 1. Run the live tier (above) on the new code.
# 2. Promote the fresh report:
cp tests/bench/reports/bench-live-<sha>.json tests/bench/baselines/baseline.json
# 3. Commit it with the change that justified the shift:
git add tests/bench/baselines/baseline.json
git commit -m "chore(bench): refresh live baseline after <reason>"
```

The `meta` block in the report records which models and commit produced the
baseline, so a future "why is this slower?" has provenance.
