# SP6 — OTel Stack Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development. Spec: `docs/superpowers/specs/2026-06-12-otel-stack-design.md` (locked decisions: LGTM all-in-one · native REST query · compose-on/bare-off).

**Goal:** Unified traces/metrics/logs from backend + worker into one `grafana/otel-lgtm` container; `ingest.step` spans over the existing `pipeline_step` seam; agents query run stats via Tempo/Loki/Prometheus REST instead of babysitting.

**Ground truth:** `pipeline_step` async contextmanager in `app/runtime/pipeline_events.py` (yields metrics dict, takes `llm=`, computes duration_ms); `app/main.py` lifespan exists; worker entry `app/worker/__main__.py`; LLM HTTP via httpx; engine at `app.core.database.engine` (async — sync core via `.sync_engine`). Compose file `munger/docker-compose.yml` (host ports in use: 3000 vite, 18000 api, 5432 pg). Baseline **188 passed, 5 deselected**.

---

### Task 1: App instrumentation (env-gated) + tests

**Files:** `requirements.txt`; create `app/observability/otel_setup.py`; modify `app/main.py`, `app/worker/__main__.py`, `app/runtime/pipeline_events.py`; test `tests/integration/test_otel.py`.

- [ ] **Deps** (install into the venv):
```
# OpenTelemetry (env-gated; active only when OTEL_EXPORTER_OTLP_ENDPOINT is set)
opentelemetry-sdk>=1.27
opentelemetry-exporter-otlp-proto-http>=1.27
opentelemetry-instrumentation-fastapi>=0.48b0
opentelemetry-instrumentation-sqlalchemy>=0.48b0
opentelemetry-instrumentation-httpx>=0.48b0
```

- [ ] **`app/observability/otel_setup.py`** — `setup_otel(service_name, *, app=None, sqlalchemy_engine=None) -> bool`:
  - `OTEL_EXPORTER_OTLP_ENDPOINT` unset → return False before importing any SDK module.
  - Active path: Resource(service.name) → TracerProvider+BatchSpanProcessor(OTLPSpanExporter), MeterProvider+PeriodicExportingMetricReader(OTLPMetricExporter), LoggerProvider+BatchLogRecordProcessor(OTLPLogExporter)+LoggingHandler on root logger; httpx auto-instrumentation always; FastAPI/SQLAlchemy when targets passed (`engine.sync_engine` for SQLAlchemy).
  - Idempotent module flag; second call only instruments new targets. Every instrumentation wrapped in try/except-log (telemetry must never break the app).
  - Verify exact import paths against INSTALLED versions (`_log_exporter` naming varies across releases).
- [ ] **Wire-up:** `app/main.py` lifespan start: `setup_otel("munger-backend", app=app, sqlalchemy_engine=engine)`; `app/worker/__main__.py`: `setup_otel("munger-worker", sqlalchemy_engine=engine)`.
- [ ] **Span seam** in `pipeline_step`: body wrapped in `trace.get_tracer("munger.ingest").start_as_current_span("ingest.step")`; attrs at entry `ingest.step_key/source_id/job_id`, at exit `ingest.duration_ms` + `ingest.llm_calls/llm_ms` and scalar metrics. No env check — with no provider the API no-op tracer makes this free. Also record the two instruments from the same seam when a meter provider is active: histogram `munger.ingest.step.duration` {step_key}, counter `munger.llm.calls` {step_key} (acquire lazily, no-op safe).
- [ ] **Tests** `tests/integration/test_otel.py`:
  - `test_setup_noop_without_env` — monkeypatch.delenv, returns False, global provider remains API default (not SDK TracerProvider).
  - `test_pipeline_step_emits_span_with_attrs` — LOCAL `TracerProvider` + `InMemorySpanExporter` + `SimpleSpanProcessor`; monkeypatch the tracer acquisition in pipeline_events (global provider is set-once per process — never set it in tests); seed a Source row (mirror tests/integration/test_llm_telemetry.py), run `pipeline_step(... llm=dummy_with_stats)`, assert one finished `ingest.step` span with `ingest.step_key=="chunk_document"` and `ingest.llm_calls==2`.
- [ ] **MUST:** full suite → **190 passed** (188+2). Commit `feat(obs): env-gated OpenTelemetry — traces/metrics/logs + pipeline_step spans (SP6)`.

### Task 2: Compose + agent recipes

**Files:** `munger/docker-compose.yml`, `munger/.env.example`, create `docs/OBSERVABILITY.md`; STATUS row flip.

- [ ] Compose service:
```yaml
  munger-lgtm:
    image: grafana/otel-lgtm:latest
    container_name: munger-lgtm
    ports:
      - "13000:3000"   # Grafana UI (host 3000 = vite)
      - "4317:4317"    # OTLP gRPC (bare-metal opt-in)
      - "4318:4318"    # OTLP HTTP
      - "3200:3200"    # Tempo REST
      - "3100:3100"    # Loki REST
      - "9090:9090"    # Prometheus REST
    restart: unless-stopped
```
  plus `OTEL_EXPORTER_OTLP_ENDPOINT=http://munger-lgtm:4318` in `munger-backend` and `munger-worker` environment blocks (compose default-on per spec).
- [ ] `.env.example`: document bare-metal opt-in (`OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318`) + "unset = off".
- [ ] `docs/OBSERVABILITY.md`: stack overview, ports table, the three agent curl recipes from the spec (Tempo tag-search→trace fetch; PromQL llm-calls-by-step; LogQL errors), Grafana anonymous-login note, boundaries (ingest_events/LangSmith stay).
- [ ] `compose config --quiet` green. STATUS: SP6 row → ✅ (after Task 3). Commit `feat(obs): LGTM compose service + agent REST recipes (SP6)`.

### Task 3: Review + ship + live verify

- [ ] Reviewer: off-mode purity (no SDK import when env unset), idempotency, exporter isolation (LGTM down ≠ pipeline impact), span attr types, compose port collisions.
- [ ] Full suite ×2; STATUS/memory; PR; auto-merge.
- [ ] Deploy: main checkout `git pull` → `docker compose up -d --build` → verify one curl per signal (Tempo search non-empty after hitting any API route; Prom up; Loki labels) — report results.
