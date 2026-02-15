"""OpenTelemetry setup for the backend.

Configures tracing and metrics providers, instruments FastAPI, and
exposes an ``InstrumentationSettings`` instance that PydanticAI agents
can use for built-in OTEL spans on every LLM call.

Enable via ``OTEL_ENABLED=true`` in the environment / .env file.
"""

from __future__ import annotations

from fastapi import FastAPI
from loguru import logger

from config import Settings


def setup_telemetry(app: FastAPI, settings: Settings) -> None:
    """Initialise OpenTelemetry providers and instrument the FastAPI app.

    Call this once during application startup.  When ``settings.otel_enabled``
    is ``False`` this function is a no-op so there is zero overhead.
    """
    if not settings.otel_enabled:
        logger.info("OpenTelemetry disabled (OTEL_ENABLED=false)")
        return

    # Import OTEL packages only when actually needed
    from opentelemetry import trace
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    resource = Resource.create(
        {
            "service.name": settings.otel_service_name,
            "service.version": "0.3.0",
        }
    )

    provider = TracerProvider(resource=resource)

    # OTLP HTTP exporter (sends to a local collector, Jaeger, SigNoz, etc.)
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

    otlp_exporter = OTLPSpanExporter(endpoint=f"{settings.otel_exporter_otlp_endpoint}/v1/traces")
    provider.add_span_processor(BatchSpanProcessor(otlp_exporter))

    # Optional: console exporter for local debugging
    if settings.otel_console_exporter:
        from opentelemetry.sdk.trace.export import ConsoleSpanExporter, SimpleSpanProcessor

        provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))

    trace.set_tracer_provider(provider)

    # Instrument FastAPI (automatic spans for every HTTP request)
    FastAPIInstrumentor.instrument_app(app)

    logger.info(
        "OpenTelemetry enabled | service={} | endpoint={}",
        settings.otel_service_name,
        settings.otel_exporter_otlp_endpoint,
    )


def get_instrumentation_settings(settings: Settings):
    """Return PydanticAI ``InstrumentationSettings`` wired to the global OTEL providers.

    Returns ``None`` when OTEL is disabled, so agents can be created with
    ``Agent(..., instrument=get_instrumentation_settings(s))`` and the
    kwarg is simply ignored when ``None``.
    """
    if not settings.otel_enabled:
        return None

    from pydantic_ai.models.instrumented import InstrumentationSettings

    return InstrumentationSettings()
