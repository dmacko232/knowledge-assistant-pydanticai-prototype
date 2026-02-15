"""Observability setup for the backend.

Supports three modes controlled by the ``OBSERVABILITY`` setting:

- ``"logfire"`` — Pydantic Logfire (set ``LOGFIRE_TOKEN`` env var)
- ``"otel"``    — raw OpenTelemetry with OTLP HTTP exporter
- ``"off"``     — no tracing / metrics (default)
"""

from __future__ import annotations

from fastapi import FastAPI
from loguru import logger

from config import Settings


def setup_telemetry(app: FastAPI, settings: Settings) -> None:
    """Initialise observability providers and instrument the FastAPI app.

    Call this once during application startup.  When ``settings.observability``
    is ``"off"`` this function is a no-op.
    """
    mode = settings.observability.lower()

    if mode == "off":
        logger.info("Observability disabled (OBSERVABILITY=off)")
        return

    if mode == "logfire":
        _setup_logfire(app, settings)
    elif mode == "otel":
        _setup_otel(app, settings)
    else:
        logger.warning("Unknown observability mode '{}', disabling", mode)


def _setup_logfire(app: FastAPI, settings: Settings) -> None:
    """Configure Pydantic Logfire and instrument FastAPI."""
    import logfire

    logfire.configure(service_name=settings.otel_service_name)
    logfire.instrument_fastapi(app)

    logger.info("Logfire enabled | service={}", settings.otel_service_name)


def _setup_otel(app: FastAPI, settings: Settings) -> None:
    """Configure raw OpenTelemetry with OTLP HTTP exporter."""
    from opentelemetry import trace
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    resource = Resource.create(
        {
            "service.name": settings.otel_service_name,
            "service.version": "0.4.0",
        }
    )

    provider = TracerProvider(resource=resource)

    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

    otlp_exporter = OTLPSpanExporter(endpoint=f"{settings.otel_exporter_otlp_endpoint}/v1/traces")
    provider.add_span_processor(BatchSpanProcessor(otlp_exporter))

    if settings.otel_console_exporter:
        from opentelemetry.sdk.trace.export import ConsoleSpanExporter, SimpleSpanProcessor

        provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))

    trace.set_tracer_provider(provider)
    FastAPIInstrumentor.instrument_app(app)

    logger.info(
        "OpenTelemetry enabled | service={} | endpoint={}",
        settings.otel_service_name,
        settings.otel_exporter_otlp_endpoint,
    )


def is_observability_active(settings: Settings) -> bool:
    """Return True when any observability backend is enabled."""
    return settings.observability.lower() in ("logfire", "otel")


def get_instrumentation_settings(settings: Settings):
    """Return PydanticAI ``InstrumentationSettings`` for agent instrumentation.

    Returns ``None`` when observability is disabled, so agents can be created
    with ``Agent(..., instrument=get_instrumentation_settings(s))`` and the
    kwarg is simply ignored when ``None``.
    """
    if not is_observability_active(settings):
        return None

    from pydantic_ai.models.instrumented import InstrumentationSettings

    return InstrumentationSettings()
