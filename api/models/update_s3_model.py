import re
from typing import Dict, Optional

from pydantic import BaseModel, Field, field_validator


class S3ResourceUpdateRequest(BaseModel):
    resource_name: Optional[str] = Field(
        None,
        description="The unique name of the resource (lowercase, alphanumeric, underscores and hyphens only).",
        json_schema_extra={"example": "example_resource_name"},
    )
    resource_title: Optional[str] = Field(
        None,
        description="The title of the resource.",
        json_schema_extra={"example": "Example Resource Title"},
    )
    owner_org: Optional[str] = Field(
        None,
        description=("The ID of the organization to which the resource belongs."),
        json_schema_extra={"example": "example_org_id"},
    )
    resource_s3: Optional[str] = Field(
        None,
        description="The S3 URL of the resource.",
        json_schema_extra={"example": "s3://bucket/path/to/resource"},
    )

    @field_validator("resource_name")
    @classmethod
    def validate_resource_name(cls, v: Optional[str]) -> Optional[str]:
        """Validate resource name format (lowercase, alphanumeric, underscores, hyphens)."""
        if v is not None and not re.match(r"^[a-z0-9_-]+$", v):
            raise ValueError(
                "resource_name must contain only lowercase letters, numbers, underscores, and hyphens"
            )
        return v

    @field_validator("resource_s3")
    @classmethod
    def validate_s3_url(cls, v: Optional[str]) -> Optional[str]:
        """Validate S3 URL format."""
        if v is not None and not v.startswith(("s3://", "http://", "https://")):
            raise ValueError(
                "resource_s3 must be a valid S3 URL (s3://, http://, or https://)"
            )
        return v

    notes: Optional[str] = Field(
        None,
        description="Additional notes about the resource.",
        json_schema_extra={"example": "Additional notes about the resource."},
    )
    extras: Optional[Dict[str, str]] = Field(
        None,
        description=(
            "Additional metadata to be added to the resource " "package as extras."
        ),
        json_schema_extra={"example": {"key1": "value1", "key2": "value2"}},
    )
