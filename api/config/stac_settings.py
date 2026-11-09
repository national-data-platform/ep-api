# api/config/stac_settings.py
"""Settings for summarising STAC collection resources (issue #405)."""

from pydantic_settings import BaseSettings


class StacSettings(BaseSettings):
    """
    How the Endpoint reads STAC collections to summarise them.

    The Endpoint reads a collection only when asked about a resource of one
    of its datasets, so turning this off is for Endpoints that must not make
    outbound requests at all.
    """

    stac_summary_enabled: bool = True
    stac_fetch_timeout_seconds: float = 10.0
    stac_max_bytes: int = 5_000_000
    stac_cache_seconds: int = 600

    model_config = {
        "env_file": ".env",
        "extra": "allow",
    }


stac_settings = StacSettings()
