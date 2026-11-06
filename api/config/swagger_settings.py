# api/config/swagger_settings.py

import logging
import re
from urllib.parse import urlparse

from pydantic import AliasChoices, Field, field_validator, model_validator
from pydantic_settings import BaseSettings

_ENDPOINT_GROUP = re.compile(r"^ndp_ep/(ep-[A-Za-z0-9_-]+)$")


def client_id_from_group_names(group_names: str) -> str:
    """The client of the first ndp_ep/ep-<config-id> group listed, or ""."""
    for name in (group_names or "").split(","):
        match = _ENDPOINT_GROUP.match(name.strip().strip("/"))
        if match:
            return match.group(1)
    return ""


class Settings(BaseSettings):
    """
    Configuration settings for the API application.

    All settings can be overridden using environment variables.
    """

    swagger_title: str = "API Documentation"
    swagger_description: str = "This is the API documentation."
    swagger_version: str = "0.34.73"
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
    # Read only to derive AUTHZ_CLIENT_ID for an Endpoint installed before it
    # existed: its .env names the group, ndp_ep/ep-<config-id>, and not the
    # client. Without this, upgrading such an Endpoint refused every request.
    group_names: str = ""

    # Access-request workflow (user requests entry → admin approves/rejects).
    # Requires a MongoDB instance reachable via MONGODB_CONNECTION_STRING
    # (reused from CatalogSettings) when turned on. Kept off by default
    # so existing deployments without MongoDB keep booting as before.
    enable_access_requests: bool = False
    access_requests_collection: str = "access_requests"

    # Tell admins when a newer ep-api release exists (issue #395). The latest
    # release is read from this URL (GitHub releases API format: tag_name,
    # html_url) and kept for the interval. Turn it off on Endpoints without
    # internet access or that should not contact GitHub.
    release_check_enabled: bool = True
    release_check_url: str = (
        "https://api.github.com/repos/national-data-platform/ep-api/releases/latest"
    )
    release_check_interval_seconds: int = 21600  # 6 hours

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

    @model_validator(mode="after")
    def client_from_the_old_group_setting(self):
        """Take AUTHZ_CLIENT_ID from GROUP_NAMES when only that is set."""
        if not self.authz_client_id:
            client = client_id_from_group_names(self.group_names)
            if client:
                self.authz_client_id = client
                logging.getLogger(__name__).warning(
                    "AUTHZ_CLIENT_ID is not set; using %s from GROUP_NAMES. "
                    "Set AUTHZ_CLIENT_ID in .env (re-running the installer "
                    "does it).",
                    client,
                )
        return self

    @property
    def aai_api_url(self) -> str:
        """The AAI API: token information, login and group management."""
        return f"{self.keycloak_url}/api"

    @property
    def keycloak_realm_url(self) -> str:
        """The realm permission decisions are asked of."""
        return f"{self.keycloak_url}/realms/{self.authz_realm}"


swagger_settings = Settings()
