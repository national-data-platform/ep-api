# api/config/rexec_settings.py

from pydantic_settings import BaseSettings


class RexecSettings(BaseSettings):
    connection: bool = False
    deployment_api_url: str = ""

    model_config = {
        "env_file": ".env",
        "extra": "allow",
        "env_prefix": "REXEC_",
    }


rexec_settings = RexecSettings()
