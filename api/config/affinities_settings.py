# api/config/affinities_settings.py
"""
Affinities API integration configuration.

This module provides configuration settings for connecting to
the NDP Affinities service for automatic registration of
datasets, services, and their relationships.
"""

from pydantic_settings import BaseSettings


class AffinitiesSettings(BaseSettings):
    """
    Configuration settings for Affinities integration.

    Attributes
    ----------
    enabled : bool
        Enable/disable Affinities integration (default: False)
    url : str
        Base URL of the Affinities API (e.g., "http://affinities-api:8000")
    ep_uuid : str
        UUID of this endpoint in Affinities, obtained when manually
        registering the endpoint in the Affinities system
    timeout : int
        Request timeout in seconds (default: 30)
    """

    enabled: bool = False
    url: str = ""
    ep_uuid: str = ""
    timeout: int = 30

    model_config = {
        "env_file": ".env",
        "extra": "allow",
        "env_prefix": "AFFINITIES_",
    }

    @property
    def is_configured(self) -> bool:
        """
        Check if Affinities integration is properly configured.

        Returns True only if enabled AND both url and ep_uuid are set.
        """
        return self.enabled and bool(self.url) and bool(self.ep_uuid)


affinities_settings = AffinitiesSettings()
