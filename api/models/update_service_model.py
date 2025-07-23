# api/models/update_service_model.py
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field, validator


class ServiceUpdateRequest(BaseModel):
    """
    Request model for service updates (PUT and PATCH operations).

    All fields are optional to allow partial updates (PATCH operations).
    For PUT operations, typically more fields would be provided.
    """

    service_name: Optional[str] = Field(
        None, description="Unique name for the service", min_length=1, max_length=100
    )
    service_title: Optional[str] = Field(
        None, description="Display title for the service", min_length=1, max_length=200
    )
    owner_org: Optional[str] = Field(
        None, description="Organization ID (must be 'services')", pattern="^services$"
    )
    service_url: Optional[str] = Field(
        None, description="URL where the service is accessible"
    )
    service_type: Optional[str] = Field(
        None,
        description="Type of service (e.g., API, Web Service, Microservice)",
        max_length=50,
    )
    notes: Optional[str] = Field(
        None, description="Additional description or notes about the service"
    )
    extras: Optional[Dict[str, Any]] = Field(
        None, description="Additional metadata as key-value pairs"
    )
    health_check_url: Optional[str] = Field(
        None, description="URL for service health check endpoint"
    )
    documentation_url: Optional[str] = Field(
        None, description="URL to service documentation"
    )

    @validator("owner_org")
    def validate_owner_org(cls, v):
        """
        Validate that owner_org is 'services' if provided.

        Parameters
        ----------
        v : str or None
            The owner_org value to validate.

        Returns
        -------
        str or None
            The validated owner_org value.

        Raises
        ------
        ValueError
            If owner_org is not 'services'.
        """
        if v is not None and v != "services":
            raise ValueError("owner_org must be 'services' for service registration")
        return v

    @validator("service_url", "health_check_url", "documentation_url")
    def validate_urls(cls, v):
        """
        Validate URL format for service-related URLs.

        Parameters
        ----------
        v : str or None
            The URL value to validate.

        Returns
        -------
        str or None
            The validated URL value.

        Raises
        ------
        ValueError
            If URL format is invalid.
        """
        if v is None:
            return v
        if not v.startswith(("http://", "https://")):
            raise ValueError("URLs must start with http:// or https://")
        return v

    class Config:
        """Pydantic configuration."""

        schema_extra = {
            "example": {
                "service_name": "updated_auth_api",
                "service_title": "Updated User Authentication API",
                "owner_org": "services",
                "service_url": "https://api.example.com/auth/v2",
                "service_type": "REST API",
                "notes": "Updated RESTful API for user authentication and authorization",
                "extras": {"version": "2.2.0", "environment": "production"},
                "health_check_url": "https://api.example.com/auth/v2/health",
                "documentation_url": "https://docs.example.com/auth-api-v2",
            }
        }
