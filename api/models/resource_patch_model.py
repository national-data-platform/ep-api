# api/models/resource_patch_model.py
from typing import Optional

from pydantic import BaseModel, Field


class ResourcePatchRequest(BaseModel):
    """
    Request model for partially updating a resource.

    All fields are optional. Only provided fields will be updated.
    """

    name: Optional[str] = Field(
        None,
        description="New name for the resource",
        min_length=1,
        max_length=255,
    )
    url: Optional[str] = Field(
        None,
        description="New URL for the resource",
    )
    description: Optional[str] = Field(
        None,
        description="New description for the resource",
    )
    format: Optional[str] = Field(
        None,
        description="New format for the resource (e.g., CSV, JSON, PDF)",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "name": "updated-resource-name",
                    "description": "Updated description for this resource",
                },
                {
                    "url": "https://example.com/new-data.csv",
                    "format": "CSV",
                },
            ]
        }
    }
