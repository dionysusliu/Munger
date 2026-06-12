# OTel Stack Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development.

**Goal:** Unified OpenTelemetry observability (traces + metrics + logs) across backend + worker, exported to a single local LGTM container (Grafana otel-lgtm: OTel collector + Tempo + Loki + Prometheus + Grafana), with **REST query recipes** so agents pull pipeline stats via plain HTTP instead of babysitting live runs (the job-4 lesson).

**Architecture:** `app/observability/otel_setup.py` — `setup_otel(service_name)` is a **complete no-op unless `OTEL_EXPORTER_OTLP_ENDPOINT` is set** (additive convention; zero overhead/zero deps touched when off). When on: OTLP-export TracerProvider/MeterProvider/LoggingHandler, plus auto-instrumentation for FastAPI (app), SQLAlchemy (engine), and httpx (LLM calls get spans for free). Called from `app/main.py` lifespan (service.name=munger-backend) and `app/worker/__main__.py` (munger-worker). Manual span seam: `pipeline_events.pipeline_step` wraps each step in a span `ingest.step` with attributes (step_key, source_id, job_id, duration + llm_calls/llm_ms from the existing metrics dict) — one contextmanager instruments the whole pipeline. Compose adds `munger-lgtm` (image `grafana/otel-lgtm`), OTLP wired via env on backend+worker; Grafana UI on host **13000** (3000 is the vite dev port), Tempo 3200 / Loki 3100 / Prometheus 9090 exposed for REST.

**Agent REST recipes (the point):** documented in `docs/OBSERVABILITY.md` —
- traces: `GET :3200/api/search?tags=service.name%3Dmunger-worker%20step_key%3Dlink_entities` → trace ids; `GET :3200/api/traces/<id>`
- metrics: `GET :9090/api/v1/query?query=...`
- logs: `GET :3100/loki/api/v1/query_range?query={service_name="munger-worker"}`

**Ground truth:** `pipeline_step` async contextmanager in `app/runtime/pipeline_events.py` (yields metrics dict, already takes `llm=` and computes duration); `app/main.py` lifespan exists (runs migrations); worker entry `app/worker/__main__.py`; LLM HTTP via httpx AsyncClient. Baseline **188 passed, 5 deselected**.

## Tasks
1. **App instrumentation** — deps (opentelemetry-sdk, exporter-otlp-proto-http, instrumentation-{fastapi,sqlalchemy,httpx}), `otel_setup.py` (env-gated, idempotent), wire main.py + worker, span in `pipeline_step` (no-op tracer when off), tests: (a) everything off w/o env (no provider installed, suite unchanged); (b) with in-memory exporter: pipeline_step emits `ingest.step` span carrying step_key + llm_calls attrs. Default suite stays green.
2. **Compose + docs** — `munger-lgtm` service + env wiring on backend/worker, `docs/OBSERVABILITY.md` (stack, ports, REST recipes incl. the three curls above + Grafana login note), STATUS row.
3. **Review + ship** — reviewer (no-op guarantee when env unset, double-instrumentation idempotency, exporter failure must never break ingest), full suite, PR, auto-merge.
