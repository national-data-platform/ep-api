# api/config/dspaces_settings.py

from pydantic_settings import BaseSettings


class DSpacesSettings(BaseSettings):
    dspaces_enabled: bool = False
    dspaces_url: str = ""

    @property
    def connection_details(self):
        return {
            "dspaces_enabled": self.dspaces_enabled,
            "dspaces_url": self.dspaces_url,
        }

    model_config = {
        "env_file": ".env",
        "extra": "allow",
    }


dspaces_settings = DSpacesSettings()
