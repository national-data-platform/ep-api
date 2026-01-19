# api/telemetry/setup.py
"""OpenTelemetry setup and instrumentation."""

import logging
from typing import Optional

from fastapi import FastAPI

from api.config.otel_settings import otel_settings

logger = logging.getLogger(__name__)

# Global tracer reference
_tracer = None


def setup_telemetry(app: FastAPI) -> bool:
    """
    Set up OpenTelemetry instrumentation for the FastAPI application.

    Parameters
    ----------
    app : FastAPI
        The FastAPI application instance to instrument.

    Returns
    -------
    bool
        True if telemetry was successfully set up, False otherwise.
    """
    global _tracer

    if not otel_settings.enabled:
        logger.info("OpenTelemetry is disabled")
        return False

    try:
        from opentelemetry import trace
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.resources import Resource, SERVICE_NAME
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
        from opentelemetry.instrumentation.requests import RequestsInstrumentor

        # Create resource with service name
        resource = Resource.create({SERVICE_NAME: otel_settings.service_name})

        # Create and set tracer provider
        provider = TracerProvider(resource=resource)

        # Configure exporter based on settings
        if otel_settings.exporter_type == "console":
            from opentelemetry.sdk.trace.export import (
                ConsoleSpanExporter,
                SimpleSpanProcessor,
            )

            processor = SimpleSpanProcessor(ConsoleSpanExporter())
            provider.add_span_processor(processor)
            logger.info("OpenTelemetry configured with console exporter")

        elif otel_settings.exporter_type == "otlp":
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
                OTLPSpanExporter,
            )
            from opentelemetry.sdk.trace.export import BatchSpanProcessor

            exporter = OTLPSpanExporter(
                endpoint=otel_settings.otlp_endpoint,
                insecure=otel_settings.otlp_insecure,
            )
            processor = BatchSpanProcessor(exporter)
            provider.add_span_processor(processor)
            logger.info(
                f"OpenTelemetry configured with OTLP exporter: {otel_settings.otlp_endpoint}"
            )

        elif otel_settings.exporter_type == "none":
            logger.info("OpenTelemetry configured without exporter (tracing only)")

        else:
            logger.warning(
                f"Unknown exporter type: {otel_settings.exporter_type}, using none"
            )

        # Set the global tracer provider
        trace.set_tracer_provider(provider)

        # Get tracer for manual instrumentation
        _tracer = trace.get_tracer(otel_settings.service_name)

        # Instrument FastAPI
        FastAPIInstrumentor.instrument_app(app)
        logger.info("FastAPI instrumented with OpenTelemetry")

        # Instrument HTTP clients
        try:
            HTTPXClientInstrumentor().instrument()
            logger.info("HTTPX client instrumented")
        except Exception as e:
            logger.debug(f"HTTPX instrumentation skipped: {e}")

        try:
            RequestsInstrumentor().instrument()
            logger.info("Requests library instrumented")
        except Exception as e:
            logger.debug(f"Requests instrumentation skipped: {e}")

        logger.info(
            f"OpenTelemetry setup complete for service: {otel_settings.service_name}"
        )
        return True

    except ImportError as e:
        logger.warning(
            f"OpenTelemetry dependencies not installed, tracing disabled: {e}"
        )
        return False
    except Exception as e:
        logger.error(f"Failed to set up OpenTelemetry: {e}")
        return False


def get_tracer():
    """
    Get the configured tracer for manual instrumentation.

    Returns
    -------
    Tracer or None
        The OpenTelemetry tracer if configured, None otherwise.
    """
    return _tracer


def create_span(name: str, attributes: Optional[dict] = None):
    """
    Create a new span for manual instrumentation.

    Parameters
    ----------
    name : str
        The name of the span.
    attributes : dict, optional
        Additional attributes to add to the span.

    Returns
    -------
    Span context manager or None
        A span context manager if tracer is configured, None otherwise.

    Example
    -------
    >>> with create_span("my_operation", {"key": "value"}) as span:
    ...     # Do work
    ...     span.set_attribute("result", "success")
    """
    if _tracer is None:
        return _NoOpSpan()

    span = _tracer.start_as_current_span(name)
    if attributes:
        span.set_attributes(attributes)
    return span


class _NoOpSpan:
    """No-op span for when telemetry is disabled."""

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def set_attribute(self, key, value):
        pass

    def set_attributes(self, attributes):
        pass

    def add_event(self, name, attributes=None):
        pass

    def record_exception(self, exception):
        pass
