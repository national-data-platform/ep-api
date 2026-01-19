# tests/test_telemetry.py
"""Tests for OpenTelemetry telemetry module."""

from unittest.mock import patch, MagicMock

from api.config.otel_settings import OTelSettings
from api.telemetry.setup import setup_telemetry, get_tracer, create_span, _NoOpSpan


class TestOTelSettings:
    """Tests for OTelSettings configuration."""

    def test_default_settings(self):
        """Test default OTel settings."""
        settings = OTelSettings()
        assert settings.enabled is False
        assert settings.service_name == "ep-api"
        assert settings.exporter_type == "console"
        assert settings.otlp_endpoint == "http://localhost:4317"
        assert settings.otlp_insecure is True

    def test_is_configured_when_disabled(self):
        """Test is_configured returns False when disabled."""
        settings = OTelSettings(enabled=False)
        assert settings.is_configured is False

    def test_is_configured_when_enabled(self):
        """Test is_configured returns True when enabled."""
        settings = OTelSettings(enabled=True)
        assert settings.is_configured is True

    def test_settings_from_env(self):
        """Test settings can be loaded from environment variables."""
        with patch.dict(
            "os.environ",
            {
                "OTEL_ENABLED": "true",
                "OTEL_SERVICE_NAME": "test-service",
                "OTEL_EXPORTER_TYPE": "otlp",
                "OTEL_OTLP_ENDPOINT": "http://collector:4317",
            },
        ):
            settings = OTelSettings()
            assert settings.enabled is True
            assert settings.service_name == "test-service"
            assert settings.exporter_type == "otlp"
            assert settings.otlp_endpoint == "http://collector:4317"


class TestSetupTelemetry:
    """Tests for setup_telemetry function."""

    def test_setup_disabled(self):
        """Test setup returns False when telemetry is disabled."""
        with patch("api.telemetry.setup.otel_settings") as mock_settings:
            mock_settings.enabled = False
            mock_app = MagicMock()

            result = setup_telemetry(mock_app)

            assert result is False

    def test_setup_with_console_exporter(self):
        """Test setup with console exporter."""
        with patch("api.telemetry.setup.otel_settings") as mock_settings:
            mock_settings.enabled = True
            mock_settings.service_name = "test-service"
            mock_settings.exporter_type = "console"

            mock_app = MagicMock()

            result = setup_telemetry(mock_app)

            assert result is True

    def test_setup_with_otlp_exporter(self):
        """Test setup with OTLP exporter."""
        with patch("api.telemetry.setup.otel_settings") as mock_settings:
            mock_settings.enabled = True
            mock_settings.service_name = "test-service"
            mock_settings.exporter_type = "otlp"
            mock_settings.otlp_endpoint = "http://localhost:4317"
            mock_settings.otlp_insecure = True

            mock_app = MagicMock()

            result = setup_telemetry(mock_app)

            assert result is True

    def test_setup_with_none_exporter(self):
        """Test setup with no exporter."""
        with patch("api.telemetry.setup.otel_settings") as mock_settings:
            mock_settings.enabled = True
            mock_settings.service_name = "test-service"
            mock_settings.exporter_type = "none"

            mock_app = MagicMock()

            result = setup_telemetry(mock_app)

            assert result is True

    def test_setup_with_unknown_exporter(self):
        """Test setup with unknown exporter type defaults to none."""
        with patch("api.telemetry.setup.otel_settings") as mock_settings:
            mock_settings.enabled = True
            mock_settings.service_name = "test-service"
            mock_settings.exporter_type = "unknown"

            mock_app = MagicMock()

            result = setup_telemetry(mock_app)

            assert result is True


class TestNoOpSpan:
    """Tests for _NoOpSpan class."""

    def test_context_manager(self):
        """Test NoOpSpan can be used as context manager."""
        span = _NoOpSpan()

        with span as s:
            assert s is span

    def test_set_attribute(self):
        """Test set_attribute does nothing."""
        span = _NoOpSpan()
        span.set_attribute("key", "value")  # Should not raise

    def test_set_attributes(self):
        """Test set_attributes does nothing."""
        span = _NoOpSpan()
        span.set_attributes({"key": "value"})  # Should not raise

    def test_add_event(self):
        """Test add_event does nothing."""
        span = _NoOpSpan()
        span.add_event("event", {"key": "value"})  # Should not raise

    def test_record_exception(self):
        """Test record_exception does nothing."""
        span = _NoOpSpan()
        span.record_exception(Exception("test"))  # Should not raise


class TestCreateSpan:
    """Tests for create_span function."""

    def test_create_span_returns_noop_when_tracer_none(self):
        """Test create_span returns NoOpSpan when tracer is not configured."""
        import api.telemetry.setup as setup_module

        # Reset tracer to None
        original_tracer = setup_module._tracer
        setup_module._tracer = None

        try:
            span = create_span("test_span")
            assert isinstance(span, _NoOpSpan)
        finally:
            setup_module._tracer = original_tracer

    def test_create_span_with_attributes(self):
        """Test create_span accepts attributes."""
        import api.telemetry.setup as setup_module

        setup_module._tracer = None

        span = create_span("test_span", {"key": "value"})
        assert isinstance(span, _NoOpSpan)


class TestGetTracer:
    """Tests for get_tracer function."""

    def test_get_tracer_returns_none_initially(self):
        """Test get_tracer returns None when not configured."""
        import api.telemetry.setup as setup_module

        original_tracer = setup_module._tracer
        setup_module._tracer = None

        try:
            tracer = get_tracer()
            assert tracer is None
        finally:
            setup_module._tracer = original_tracer


class TestTelemetryIntegration:
    """Integration tests for telemetry with FastAPI."""

    def test_app_starts_with_telemetry_disabled(self):
        """Test FastAPI app starts correctly with telemetry disabled."""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        with patch("api.telemetry.setup.otel_settings") as mock_settings:
            mock_settings.enabled = False

            app = FastAPI()

            @app.get("/test")
            def test_endpoint():
                return {"status": "ok"}

            result = setup_telemetry(app)
            assert result is False

            client = TestClient(app)
            response = client.get("/test")
            assert response.status_code == 200
            assert response.json() == {"status": "ok"}

    def test_app_starts_with_telemetry_enabled(self):
        """Test FastAPI app starts correctly with telemetry enabled."""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        with patch("api.telemetry.setup.otel_settings") as mock_settings:
            mock_settings.enabled = True
            mock_settings.service_name = "test-app"
            mock_settings.exporter_type = "none"

            app = FastAPI()

            @app.get("/test")
            def test_endpoint():
                return {"status": "ok"}

            result = setup_telemetry(app)
            assert result is True

            client = TestClient(app)
            response = client.get("/test")
            assert response.status_code == 200
            assert response.json() == {"status": "ok"}
