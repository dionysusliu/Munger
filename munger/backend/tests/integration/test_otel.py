"""Tests for SP6 OpenTelemetry instrumentation (Task 1).

Two tests per the plan:
  test_setup_noop_without_env   — setup_otel returns False with env unset;
                                   global provider remains the API default
                                   (NOT an SDK TracerProvider).
  test_pipeline_step_emits_span_with_attrs
                                — local TracerProvider + InMemorySpanExporter
                                   via monkeypatched _get_tracer; asserts one
                                   finished "ingest.step" span with the
                                   expected attributes.

INVARIANT: neither test sets the global tracer provider (set-once per process).
"""

from __future__ import annotations

import pytest

import opentelemetry.trace as _otel_trace
import app.runtime.pipeline_events as _pe
from tests.conftest import run_async


# ---------------------------------------------------------------------------
# Shared dummy LLM (mirrors test_llm_telemetry.py)
# ---------------------------------------------------------------------------

class _DummyLLM:
    def __init__(self):
        self.stats: dict[str, int] = {"calls": 0, "ms": 0}


# ---------------------------------------------------------------------------
# Test 1: noop when OTEL_EXPORTER_OTLP_ENDPOINT is absent
# ---------------------------------------------------------------------------


def test_setup_noop_without_env(monkeypatch):
    """setup_otel returns False and never touches the global tracer provider."""
    monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)

    from app.observability.otel_setup import setup_otel
    result = setup_otel("test-service")

    assert result is False, "setup_otel must return False when env var is absent"

    # Global provider must still be the API default / proxy — NOT an SDK provider.
    provider_module = type(_otel_trace.get_tracer_provider()).__module__
    assert not provider_module.startswith("opentelemetry.sdk"), (
        f"Global tracer provider must NOT be an SDK provider after noop; "
        f"got type from module: {provider_module!r}"
    )


# ---------------------------------------------------------------------------
# Test 2: pipeline_step emits a span with the expected attributes
# ---------------------------------------------------------------------------


def test_pipeline_step_emits_span_with_attrs(create_source, monkeypatch):
    """pipeline_step records an 'ingest.step' span via a LOCAL provider (no global mutation)."""
    from opentelemetry.sdk.trace import TracerProvider as _SDKTracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

    # Build a local (non-global) provider backed by an in-memory exporter.
    exporter = InMemorySpanExporter()
    local_provider = _SDKTracerProvider()
    local_provider.add_span_processor(SimpleSpanProcessor(exporter))
    local_tracer = local_provider.get_tracer("munger.ingest")

    # Patch the module-level helper so pipeline_step uses OUR tracer,
    # not the global proxy (which is a no-op in test runs).
    monkeypatch.setattr(_pe, "_get_tracer", lambda: local_tracer)

    # Seed a source row.
    source = create_source(title="OTel span attr test")
    dummy = _DummyLLM()

    async def _run():
        async with _pe.pipeline_step(
            source_id=source.id,
            job_id=42,
            step_key="chunk_document",
            llm=dummy,
        ) as metrics:
            # Simulate 2 LLM calls inside this step.
            dummy.stats["calls"] += 2
            dummy.stats["ms"] += 80

    run_async(_run())

    # Verify exactly one finished span.
    finished = exporter.get_finished_spans()
    assert len(finished) == 1, f"expected 1 span, got {len(finished)}"

    span = finished[0]
    assert span.name == "ingest.step", f"unexpected span name: {span.name!r}"

    attrs = span.attributes or {}
    assert attrs.get("ingest.step_key") == "chunk_document", (
        f"ingest.step_key wrong: {attrs.get('ingest.step_key')!r}"
    )
    assert attrs.get("ingest.llm_calls") == 2, (
        f"ingest.llm_calls wrong: {attrs.get('ingest.llm_calls')!r}"
    )

    # Global provider must still be the API default (never mutated by this test).
    provider_module = type(_otel_trace.get_tracer_provider()).__module__
    assert not provider_module.startswith("opentelemetry.sdk"), (
        f"Global tracer provider was mutated during span test; module: {provider_module!r}"
    )
