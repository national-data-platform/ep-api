from pydantic_settings import BaseSettings


class S3Settings(BaseSettings):
    """S3-compatible storage configuration settings."""
    
    s3_enabled: bool = False
    s3_endpoint: str = "localhost:9000"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin123"
    s3_secure: bool = False
    s3_region: str = "us-east-1"

    model_config = {
        "env_file": ".env",
        "extra": "allow",
    }

    @property
    def enabled(self) -> bool:
        """Get enabled status."""
        return self.s3_enabled

    @property
    def endpoint(self) -> str:
        """Get endpoint."""
        return self.s3_endpoint

    @property
    def access_key(self) -> str:
        """Get access key."""
        return self.s3_access_key

    @property
    def secret_key(self) -> str:
        """Get secret key."""
        return self.s3_secret_key

    @property
    def secure(self) -> bool:
        """Get secure flag."""
        return self.s3_secure

    @property
    def region(self) -> str:
        """Get region."""
        return self.s3_region

    @property
    def is_configured(self) -> bool:
        """Check if S3 is properly configured."""
        return (
            self.enabled
            and bool(self.endpoint)
            and bool(self.access_key)
            and bool(self.secret_key)
        )


s3_settings = S3Settings()