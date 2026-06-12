"""OTel bootstrap — env-gated, idempotent, telemetry-safe.

Returns False immediately (no SDK objects created) when
``OTEL_EXPORTER_OTLP_ENDPOINT`` is unset, giving a complete no-op in bare
uvicorn / pytest runs.

Import-path notes for opentelemetry-sdk==1.42.1:
  LoggerProvider / LoggingHandler    → opentelemetry.sdk._logs
  BatchLogRecordProcessor            → opentelemetry.sdk._logs._internal.export
  set_logger_provider                → opentelemetry._logs
  OTLPLogExporter                    → opentelemetry.exporter.otlp.proto.http._log_exporter
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

# Module-level flags — never touch the global provider a second time.
_initialized: bool = False
_httpx_instrumented: bool = False


def setup_otel(
    service_name: str,
    *,
    app=None,
    sqlalchemy_engine=None,
) -> bool:
    """Configure OpenTelemetry traces/metrics/logs for this process.

    Parameters
    ----------
    service_name:
        ``service.name`` resource attribute (e.g. ``"munger-backend"``).
    app:
        FastAPI application instance.  When provided, FastAPI ASGI
        instrumentation is activated.
    sqlalchemy_engine:
        Async SQLAlchemy engine (``create_async_engine`` result).  When
        provided, ``engine.sync_engine`` is passed to the SQLAlchemy
        instrumentor.

    Returns
    -------
    bool
        ``True`` when OTel is active, ``False`` when the env var is absent.
    """
    global _initialized, _httpx_instrumented

    # Hard invariant: no SDK import when env var is unset.
    import os
    endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT")
    if not endpoint:
        return False

    # -----------------------------------------------------------------
    # All SDK imports live here — only reached when env var is set.
    # -----------------------------------------------------------------
    from opentelemetry import trace
    from opentelemetry.metrics import set_meter_provider
    from opentelemetry._logs import set_logger_provider
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
    # sdk._logs (not sdk.logs) is the correct path for 1.42.x
    from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
    from opentelemetry.sdk._logs._internal.export import BatchLogRecordProcessor
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
    from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter

    if not _initialized:
        resource = Resource.create({"service.name": service_name})

        # --- Traces ---
        try:
            tracer_provider = TracerProvider(resource=resource)
            tracer_provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
            trace.set_tracer_provider(tracer_provider)
        except Exception:
            logger.exception("OTel: failed to configure tracer provider")

        # --- Metrics ---
        try:
            meter_provider = MeterProvider(
                resource=resource,
                metric_readers=[PeriodicExportingMetricReader(OTLPMetricExporter())],
            )
            set_meter_provider(meter_provider)
        except Exception:
            logger.exception("OTel: failed to configure meter provider")

        # --- Logs ---
        try:
            import logging as _logging
            logger_provider = LoggerProvider(resource=resource)
            logger_provider.add_log_record_processor(
                BatchLogRecordProcessor(OTLPLogExporter())
            )
            set_logger_provider(logger_provider)
            handler = LoggingHandler(
                level=_logging.NOTSET, logger_provider=logger_provider
            )
            _logging.getLogger().addHandler(handler)
        except Exception:
            logger.exception("OTel: failed to configure logger provider")

        _initialized = True
        logger.info("OTel: providers configured (service=%s, endpoint=%s)", service_name, endpoint)

    _instrument_targets(app=app, sqlalchemy_engine=sqlalchemy_engine)
    return True


def _instrument_targets(*, app, sqlalchemy_engine) -> None:
    """Instrument newly-supplied targets; idempotent per target."""
    global _httpx_instrumented

    # httpx — instrument once; covers every LLM / OpenRouter HTTP call.
    if not _httpx_instrumented:
        try:
            from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
            HTTPXClientInstrumentor().instrument()
            _httpx_instrumented = True
            logger.debug("OTel: httpx instrumented")
        except Exception:
            logger.exception("OTel: failed to instrument httpx")

    # FastAPI — when app is provided.
    if app is not None:
        try:
            from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
            FastAPIInstrumentor.instrument_app(app)
            logger.debug("OTel: FastAPI instrumented")
        except Exception:
            logger.exception("OTel: failed to instrument FastAPI")

    # SQLAlchemy — when engine is provided; uses sync_engine under the hood.
    if sqlalchemy_engine is not None:
        try:
            from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
            SQLAlchemyInstrumentor().instrument(engine=sqlalchemy_engine.sync_engine)
            logger.debug("OTel: SQLAlchemy instrumented")
        except Exception:
            logger.exception("OTel: failed to instrument SQLAlchemy")
