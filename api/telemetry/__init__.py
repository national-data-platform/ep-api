# api/telemetry/__init__.py
"""OpenTelemetry instrumentation module."""

from .setup import setup_telemetry, get_tracer

__all__ = ["setup_telemetry", "get_tracer"]
