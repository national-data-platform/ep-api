# api/config/swagger_settings.py

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Configuration settings for the API application.

    All settings can be overridden using environment variables.
    """

    swagger_title: str = "API Documentation"
    swagger_description: str = "This is the API documentation."
    swagger_version: str = "1.0.0"
    is_public: bool = True
    metrics_endpoint: str = "https://federation.ndp.utah.edu/metrics/"
    organization: str = "Unknown Organization"
    use_jupyterlab: bool = False
    jupyter_url: str = "https://jupyter.org/try-jupyter/lab/"
    test_token: str = "testing_token"
    auth_api_url: str = "https://idp-test.nationaldataplatform.org/client_admin/information"
    model_config = {
        "env_file": ".env",
        "extra": "allow",
    }


swagger_settings = Settings()
