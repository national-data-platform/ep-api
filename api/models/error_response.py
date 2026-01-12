# api/models/error_response.py
"""Standardized error response models."""

from datetime import datetime, timezone
from typing import Any, Optional

from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    """
    Standardized error response model.

    This model provides a consistent structure for all API error responses,
    including correlation ID for request tracing.
    """

    error: str = Field(
        ...,
        description="Error type or category",
        examples=["ValidationError", "NotFound", "Unauthorized"],
    )
    detail: Any = Field(
        ...,
        description="Detailed error message or structured error information",
        examples=["Resource not found", {"field": "name", "message": "Required"}],
    )
    correlation_id: Optional[str] = Field(
        None,
        description="Unique identifier for request tracing",
        examples=["550e8400-e29b-41d4-a716-446655440000"],
    )
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO 8601 timestamp when the error occurred",
        examples=["2026-01-07T19:30:00+00:00"],
    )
    path: Optional[str] = Field(
        None,
        description="Request path that caused the error",
        examples=["/dataset/123"],
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "error": "NotFound",
                    "detail": "Dataset with ID '123' not found",
                    "correlation_id": "550e8400-e29b-41d4-a716-446655440000",
                    "timestamp": "2026-01-07T19:30:00+00:00",
                    "path": "/dataset/123",
                }
            ]
        }
    }


class ValidationErrorDetail(BaseModel):
    """Detail for a single validation error."""

    loc: list[str] = Field(
        ...,
        description="Location of the error (field path)",
        examples=[["body", "name"]],
    )
    msg: str = Field(..., description="Error message", examples=["field required"])
    type: str = Field(..., description="Error type", examples=["value_error.missing"])


class ValidationErrorResponse(ErrorResponse):
    """Specialized error response for validation errors."""

    error: str = "ValidationError"
    detail: list[ValidationErrorDetail] = Field(
        ..., description="List of validation errors"
    )
