# api/config/swagger_settings.py

from pydantic import SecretStr
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Configuration settings for the API application.

    All settings can be overridden using environment variables.
    """

    swagger_title: str = "API Documentation"
    swagger_description: str = "This is the API documentation."
    swagger_version: str = "0.34.85"
    root_path: str = ""  # API root path prefix (e.g., "/test" or "")
    is_public: bool = True
    metrics_endpoint: str = "https://federation.ndp.utah.edu/metrics/"
    metrics_interval_seconds: int = 3300  # 55 minutes
    organization: str = "Unknown Organization"
    ep_name: str = "Unknown EP"
    use_jupyterlab: bool = False
    jupyter_url: str = "https://jupyter.org/try-jupyter/lab/"
    # Off unless set: a Bearer token equal to it is accepted as ndp_admin
    # without contacting AUTH_API_URL (issue #383).
    test_token: str = ""
    auth_api_url: str = "https://idp.nationaldataplatform.org/temp/information"
    enable_group_based_access: bool = False
    group_names: str = ""  # Comma-separated list of allowed groups

    # The confidential Keycloak client the Federation created for this
    # Endpoint (ep-<config-id>), for client-credentials tokens (issue #412).
    # Not the browser sign-in client (OIDC_CLIENT_ID, read by the UI only).
    oidc_service_client_id: str = ""
    oidc_service_client_secret: SecretStr = SecretStr("")

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


swagger_settings = Settings()
