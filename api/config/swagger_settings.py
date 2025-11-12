# api/config/swagger_settings.py

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Configuration settings for the API application.

    All settings can be overridden using environment variables.
    """

    swagger_title: str = "API Documentation"
    swagger_description: str = "This is the API documentation."
    swagger_version: str = "0.3.2"
    root_path: str = ""  # API root path prefix (e.g., "/test" or "")
    is_public: bool = True
    metrics_endpoint: str = "https://federation.ndp.utah.edu/metrics/"
    metrics_interval_seconds: int = 3300  # 55 minutes
    organization: str = "Unknown Organization"
    ep_name: str = "Unknown EP"
    use_jupyterlab: bool = False
    jupyter_url: str = "https://jupyter.org/try-jupyter/lab/"
    test_token: str = "testing_token"
    auth_api_url: str = "https://idp.nationaldataplatform.org/temp/information"
    enable_organization_based_access: bool = False

    model_config = {
        "env_file": ".env",
        "extra": "allow",
    }


swagger_settings = Settings()
