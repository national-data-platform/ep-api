# tests/test_error_response_model.py
"""Tests for error response models."""

import pytest
from datetime import datetime, timezone

from api.models.error_response import (
    ErrorResponse,
    ValidationErrorDetail,
    ValidationErrorResponse,
)


class TestErrorResponse:
    """Tests for ErrorResponse model."""

    def test_creates_with_required_fields(self):
        """Test creating ErrorResponse with required fields."""
        response = ErrorResponse(
            error="NotFound",
            detail="Resource not found",
        )

        assert response.error == "NotFound"
        assert response.detail == "Resource not found"
        assert response.correlation_id is None
        assert response.path is None
        assert response.timestamp is not None

    def test_creates_with_all_fields(self):
        """Test creating ErrorResponse with all fields."""
        response = ErrorResponse(
            error="BadRequest",
            detail="Invalid input",
            correlation_id="abc-123",
            path="/api/resource",
            timestamp="2026-01-07T19:00:00+00:00",
        )

        assert response.error == "BadRequest"
        assert response.detail == "Invalid input"
        assert response.correlation_id == "abc-123"
        assert response.path == "/api/resource"
        assert response.timestamp == "2026-01-07T19:00:00+00:00"

    def test_detail_accepts_string(self):
        """Test that detail accepts string."""
        response = ErrorResponse(
            error="Error",
            detail="Simple error message",
        )

        assert response.detail == "Simple error message"

    def test_detail_accepts_dict(self):
        """Test that detail accepts dict."""
        response = ErrorResponse(
            error="Error",
            detail={"field": "name", "message": "required"},
        )

        assert response.detail == {"field": "name", "message": "required"}

    def test_detail_accepts_list(self):
        """Test that detail accepts list."""
        response = ErrorResponse(
            error="Error",
            detail=[{"loc": ["body", "name"], "msg": "required"}],
        )

        assert len(response.detail) == 1

    def test_timestamp_auto_generated(self):
        """Test that timestamp is auto-generated."""
        before = datetime.now(timezone.utc)
        response = ErrorResponse(error="Error", detail="test")
        after = datetime.now(timezone.utc)

        # Parse timestamp
        timestamp = datetime.fromisoformat(response.timestamp)

        assert before <= timestamp <= after

    def test_serializes_to_json(self):
        """Test that model serializes to JSON correctly."""
        response = ErrorResponse(
            error="NotFound",
            detail="Resource not found",
            correlation_id="test-123",
            path="/api/test",
        )

        json_data = response.model_dump()

        assert json_data["error"] == "NotFound"
        assert json_data["detail"] == "Resource not found"
        assert json_data["correlation_id"] == "test-123"
        assert json_data["path"] == "/api/test"


class TestValidationErrorDetail:
    """Tests for ValidationErrorDetail model."""

    def test_creates_with_all_fields(self):
        """Test creating ValidationErrorDetail with all fields."""
        detail = ValidationErrorDetail(
            loc=["body", "name"],
            msg="field required",
            type="value_error.missing",
        )

        assert detail.loc == ["body", "name"]
        assert detail.msg == "field required"
        assert detail.type == "value_error.missing"

    def test_loc_accepts_nested_path(self):
        """Test that loc accepts nested path."""
        detail = ValidationErrorDetail(
            loc=["body", "user", "address", "city"],
            msg="invalid city",
            type="value_error",
        )

        assert len(detail.loc) == 4


class TestValidationErrorResponse:
    """Tests for ValidationErrorResponse model."""

    def test_has_validation_error_type(self):
        """Test that error type is ValidationError."""
        response = ValidationErrorResponse(
            detail=[
                ValidationErrorDetail(
                    loc=["body", "name"],
                    msg="required",
                    type="value_error.missing",
                )
            ]
        )

        assert response.error == "ValidationError"

    def test_accepts_multiple_errors(self):
        """Test that detail accepts multiple validation errors."""
        response = ValidationErrorResponse(
            detail=[
                ValidationErrorDetail(
                    loc=["body", "name"],
                    msg="required",
                    type="value_error.missing",
                ),
                ValidationErrorDetail(
                    loc=["body", "email"],
                    msg="invalid email",
                    type="value_error.email",
                ),
            ]
        )

        assert len(response.detail) == 2
        assert response.detail[0].loc == ["body", "name"]
        assert response.detail[1].loc == ["body", "email"]
