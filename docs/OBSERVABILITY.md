# Observability (SP6) — OTel stack

One container (`munger-lgtm` = OTel Collector + Tempo + Loki + Prometheus + Grafana) receives
traces/metrics/logs from `munger-backend` and `munger-worker` (preset in compose; bare-metal and
pytest are OFF unless `OTEL_EXPORTER_OTLP_ENDPOINT` is set).

| Port | Surface |
|---|---|
| 13001 | Grafana UI (anonymous login enabled by the lgtm image) |
| 3200 | Tempo trace REST |
| 3100 | Loki LogQL REST |
| 9090 | Prometheus PromQL REST |
| 4317/4318 | OTLP in (gRPC/HTTP) |

Every ingest step runs inside an `ingest.step` span with attributes `ingest.step_key`,
`ingest.source_id`, `ingest.job_id`, `ingest.duration_ms`, `ingest.llm_calls`, `ingest.llm_ms`.
HTTP (FastAPI), SQL (SQLAlchemy), and LLM calls (httpx) are auto-instrumented child spans.
Metrics: `munger.ingest.step.duration` histogram + `munger.llm.calls` counter, both tagged `step_key`.

## Agent recipes (plain REST — no babysitting)

**Where did this run spend time?** (find traces for a source's link step, then fetch the tree)
```bash
curl -s "http://localhost:3200/api/search?tags=service.name%3Dmunger-worker%20ingest.step_key%3Dlink_entities&limit=5"
curl -s "http://localhost:3200/api/traces/<traceID-from-search>"
```

**LLM burn by step (trend):**
```bash
curl -s 'http://localhost:9090/api/v1/query?query=sum(munger_llm_calls_total)%20by%20(step_key)'
# step durations p95:
curl -s 'http://localhost:9090/api/v1/query?query=histogram_quantile(0.95,sum(rate(munger_ingest_step_duration_bucket[15m]))by(le,step_key))'
```

**Errors in the worker (last hour):**
```bash
curl -sG "http://localhost:3100/loki/api/v1/query_range" \
  --data-urlencode 'query={service_name="munger-worker"} |= "ERROR"' \
  --data-urlencode "start=$(($(date +%s)-3600))000000000"
```

Note: exact Prometheus metric names are the OTel→Prom renderings of `munger.ingest.step.duration`
and `munger.llm.calls`; list what exists with `curl -s localhost:9090/api/v1/label/__name__/values | grep munger`.

## Boundaries
- `ingest_events` stays — it feeds the product UI (DAG/Gantt/stage drawer).
- LangSmith stays — LLM-semantic traces (prompts/completions).
- This stack is the engineering layer: cross-service timing, errors, trends.
