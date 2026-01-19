# api/config/otel_settings.py
"""OpenTelemetry configuration settings."""

from pydantic_settings import BaseSettings


class OTelSettings(BaseSettings):
    """OpenTelemetry configuration."""

    enabled: bool = False
    service_name: str = "ep-api"
    exporter_type: str = "console"  # "console", "otlp", "none"
    otlp_endpoint: str = "http://localhost:4317"
    otlp_insecure: bool = True

    class Config:
        env_prefix = "OTEL_"

    @property
    def is_configured(self) -> bool:
        """Check if OTEL is enabled and properly configured."""
        return self.enabled


otel_settings = OTelSettings()
