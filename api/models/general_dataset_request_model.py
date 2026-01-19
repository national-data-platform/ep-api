# api/models/general_dataset_request_model.py

import re
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class ResourceRequest(BaseModel):
    """
    Model for resource definition within a general dataset request.

    Represents a single resource (file, URL, etc.) that belongs to a dataset.
    """

    url: str = Field(..., description="URL or path to the resource")
    name: str = Field(..., description="Name identifier for the resource")

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Validate that URL is not empty and has a valid format."""
        if not v or not v.strip():
            raise ValueError("url cannot be empty")
        # Basic URL validation - must start with http://, https://, s3://, or be a path
        if not re.match(r"^(https?://|s3://|/|\.)", v):
            raise ValueError(
                "url must be a valid URL (http://, https://, s3://) or a path"
            )
        return v

    format: Optional[str] = Field(
        None, description="Format of the resource (CSV, JSON, etc.)"
    )
    description: Optional[str] = Field(None, description="Description of the resource")
    mimetype: Optional[str] = Field(None, description="MIME type of the resource")
    size: Optional[int] = Field(None, description="Size of the resource in bytes")


class GeneralDatasetRequest(BaseModel):
    """
    Model for creating a general dataset in CKAN.

    This model provides a flexible interface for creating datasets without
    being tied to specific resource types like S3, Kafka, or URL.
    """

    name: str = Field(
        ...,
        description="Unique name for the dataset (lowercase, alphanumeric, underscores and hyphens only)",
    )
    title: str = Field(..., description="Human-readable title of the dataset")
    owner_org: str = Field(..., description="Organization ID that owns this dataset")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate dataset name format (lowercase, alphanumeric, underscores, hyphens)."""
        if not re.match(r"^[a-z0-9_-]+$", v):
            raise ValueError(
                "name must contain only lowercase letters, numbers, underscores, and hyphens"
            )
        return v

    notes: Optional[str] = Field(
        None, description="Description or notes about the dataset"
    )
    tags: Optional[List[str]] = Field(
        None, description="List of tags for categorizing the dataset"
    )
    groups: Optional[List[str]] = Field(
        None, description="List of groups for the dataset"
    )
    extras: Optional[Dict[str, Any]] = Field(
        None, description="Additional metadata as key-value pairs"
    )
    resources: Optional[List[ResourceRequest]] = Field(
        None, description="List of resources associated with this dataset"
    )
    private: Optional[bool] = Field(
        False, description="Whether the dataset is private or public"
    )
    license_id: Optional[str] = Field(
        None, description="License identifier for the dataset"
    )
    version: Optional[str] = Field(None, description="Version of the dataset")


class GeneralDatasetUpdateRequest(BaseModel):
    """
    Model for updating an existing general dataset in CKAN.

    All fields are optional to allow partial updates (PATCH operations).
    """

    name: Optional[str] = Field(
        None,
        description="Unique name for the dataset (lowercase, alphanumeric, underscores and hyphens only)",
    )
    title: Optional[str] = Field(
        None, description="Human-readable title of the dataset"
    )
    owner_org: Optional[str] = Field(
        None, description="Organization ID that owns this dataset"
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        """Validate dataset name format (lowercase, alphanumeric, underscores, hyphens)."""
        if v is not None and not re.match(r"^[a-z0-9_-]+$", v):
            raise ValueError(
                "name must contain only lowercase letters, numbers, underscores, and hyphens"
            )
        return v

    notes: Optional[str] = Field(
        None, description="Description or notes about the dataset"
    )
    tags: Optional[List[str]] = Field(
        None, description="List of tags for categorizing the dataset"
    )
    groups: Optional[List[str]] = Field(
        None, description="List of groups for the dataset"
    )
    extras: Optional[Dict[str, Any]] = Field(
        None, description="Additional metadata as key-value pairs"
    )
    resources: Optional[List[ResourceRequest]] = Field(
        None, description="List of resources associated with this dataset"
    )
    private: Optional[bool] = Field(
        None, description="Whether the dataset is private or public"
    )
    license_id: Optional[str] = Field(
        None, description="License identifier for the dataset"
    )
    version: Optional[str] = Field(None, description="Version of the dataset")
