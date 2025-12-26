# api/config/dspaces_settings.py

from pydantic_settings import BaseSettings


class DSpacesSettings(BaseSettings):
    dspaces_enabled: bool = False
    dspaces_url: str = ""
    # Controls when to auto-stage data in DataSpaces on registration
    # Options: "none", "url", "s3", "kafka", "all"
    dspaces_registration: str = "none"

    @property
    def connection_details(self):
        return {
            "dspaces_enabled": self.dspaces_enabled,
            "dspaces_url": self.dspaces_url,
            "dspaces_registration": self.dspaces_registration,
        }

    def should_stage(self, resource_type: str) -> bool:
        """Check if staging should be enabled for a resource type."""
        if not self.dspaces_enabled or not self.dspaces_url:
            return False
        if self.dspaces_registration == "all":
            return True
        if self.dspaces_registration == "none":
            return False
        # Check if resource type matches the registration setting
        return resource_type.lower() == self.dspaces_registration.lower()

    model_config = {
        "env_file": ".env",
        "extra": "allow",
    }


dspaces_settings = DSpacesSettings()
