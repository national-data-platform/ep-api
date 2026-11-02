# api/config/swagger_settings.py

from urllib.parse import urlparse

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Configuration settings for the API application.

    All settings can be overridden using environment variables.
    """

    swagger_title: str = "API Documentation"
    swagger_description: str = "This is the API documentation."
    swagger_version: str = "0.34.66"
    root_path: str = ""  # API root path prefix (e.g., "/test" or "")
    is_public: bool = True
    metrics_endpoint: str = "https://federation.ndp.utah.edu/metrics/"
    metrics_interval_seconds: int = 3300  # 55 minutes
    organization: str = "Unknown Organization"
    ep_name: str = "Unknown EP"
    use_jupyterlab: bool = False
    jupyter_url: str = "https://jupyter.org/try-jupyter/lab/"
    # Off unless set: a Bearer token equal to it passes every permission gate
    # without contacting the AAI API or Keycloak (issue #383).
    test_token: str = ""

    # The identity provider's host: the AAI API (aai_api_url) and the realm
    # (keycloak_realm_url) are paths on it. AUTH_API_URL, the old name, is
    # still read when KEYCLOAK_URL is not set.
    keycloak_url: str = Field(
        default="https://idp.nationaldataplatform.org",
        validation_alias=AliasChoices("keycloak_url", "auth_api_url"),
    )
    # This Endpoint's Keycloak client (ep-<config-id>), whose gates decide
    # every permission, and the realm it is in.
    authz_client_id: str = ""
    authz_realm: str = "NDP"

    # Access-request workflow (user requests entry → admin approves/rejects).
    # Requires a MongoDB instance reachable via MONGODB_CONNECTION_STRING
    # (reused from CatalogSettings) when turned on. Kept off by default
    # so existing deployments without MongoDB keep booting as before.
    enable_access_requests: bool = False
    access_requests_collection: str = "access_requests"

    model_config = {
        "env_file": ".env",
        "extra": "allow",
    }

    @field_validator("keycloak_url")
    @classmethod
    def keep_only_the_host(cls, value):
        """Drop a path, such as the /temp/information AUTH_API_URL carried."""
        parsed = urlparse(value)
        return f"{parsed.scheme}://{parsed.netloc}" if parsed.netloc else value

    @property
    def aai_api_url(self) -> str:
        """The AAI API: token information, login and group management."""
        return f"{self.keycloak_url}/api"

    @property
    def keycloak_realm_url(self) -> str:
        """The realm permission decisions are asked of."""
        return f"{self.keycloak_url}/realms/{self.authz_realm}"


swagger_settings = Settings()
