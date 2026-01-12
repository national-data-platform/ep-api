# tests/test_exception_handlers.py
"""Tests for global exception handlers."""

import pytest
from unittest.mock import MagicMock, patch
from fastapi import HTTPException
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError

from api.exceptions.handlers import (
    http_exception_handler,
    validation_exception_handler,
    generic_exception_handler,
    _build_error_response,
)


class TestBuildErrorResponse:
    """Tests for _build_error_response helper."""

    @pytest.fixture
    def mock_request(self):
        """Create mock request."""
        mock = MagicMock()
        mock.url.path = "/test/path"
        return mock

    @patch("api.exceptions.handlers.get_correlation_id")
    def test_builds_complete_response(self, mock_get_id, mock_request):
        """Test that response includes all required fields."""
        mock_get_id.return_value = "test-correlation-id"

        response = _build_error_response(
            error_type="TestError",
            detail="Test detail message",
            status_code=400,
            request=mock_request,
        )

        assert response.status_code == 400
        # Parse response body
        import json

        body = json.loads(response.body)

        assert body["error"] == "TestError"
        assert body["detail"] == "Test detail message"
        assert body["correlation_id"] == "test-correlation-id"
        assert body["path"] == "/test/path"
        assert "timestamp" in body

    @patch("api.exceptions.handlers.get_correlation_id")
    def test_handles_dict_detail(self, mock_get_id, mock_request):
        """Test that dict detail is preserved."""
        mock_get_id.return_value = "test-id"

        response = _build_error_response(
            error_type="ComplexError",
            detail={"field": "name", "issue": "required"},
            status_code=422,
            request=mock_request,
        )

        import json

        body = json.loads(response.body)

        assert body["detail"] == {"field": "name", "issue": "required"}


class TestHttpExceptionHandler:
    """Tests for http_exception_handler."""

    @pytest.fixture
    def mock_request(self):
        """Create mock request."""
        mock = MagicMock()
        mock.url.path = "/api/resource"
        return mock

    @pytest.mark.asyncio
    @patch("api.exceptions.handlers.get_correlation_id")
    async def test_handles_404(self, mock_get_id, mock_request):
        """Test handling of 404 Not Found."""
        mock_get_id.return_value = "corr-123"
        exc = HTTPException(status_code=404, detail="Resource not found")

        response = await http_exception_handler(mock_request, exc)

        assert response.status_code == 404
        import json

        body = json.loads(response.body)
        assert body["error"] == "NotFound"
        assert body["detail"] == "Resource not found"

    @pytest.mark.asyncio
    @patch("api.exceptions.handlers.get_correlation_id")
    async def test_handles_401(self, mock_get_id, mock_request):
        """Test handling of 401 Unauthorized."""
        mock_get_id.return_value = "corr-456"
        exc = HTTPException(status_code=401, detail="Invalid token")

        response = await http_exception_handler(mock_request, exc)

        assert response.status_code == 401
        import json

        body = json.loads(response.body)
        assert body["error"] == "Unauthorized"

    @pytest.mark.asyncio
    @patch("api.exceptions.handlers.get_correlation_id")
    async def test_handles_500(self, mock_get_id, mock_request):
        """Test handling of 500 Internal Server Error."""
        mock_get_id.return_value = "corr-789"
        exc = HTTPException(status_code=500, detail="Database error")

        response = await http_exception_handler(mock_request, exc)

        assert response.status_code == 500
        import json

        body = json.loads(response.body)
        assert body["error"] == "InternalServerError"

    @pytest.mark.asyncio
    @patch("api.exceptions.handlers.get_correlation_id")
    async def test_handles_unknown_status(self, mock_get_id, mock_request):
        """Test handling of unmapped status code."""
        mock_get_id.return_value = "corr-000"
        exc = HTTPException(status_code=418, detail="I'm a teapot")

        response = await http_exception_handler(mock_request, exc)

        assert response.status_code == 418
        import json

        body = json.loads(response.body)
        assert body["error"] == "HTTPError"


class TestValidationExceptionHandler:
    """Tests for validation_exception_handler."""

    @pytest.fixture
    def mock_request(self):
        """Create mock request."""
        mock = MagicMock()
        mock.url.path = "/api/create"
        return mock

    @pytest.mark.asyncio
    @patch("api.exceptions.handlers.get_correlation_id")
    async def test_handles_request_validation_error(self, mock_get_id, mock_request):
        """Test handling of RequestValidationError."""
        mock_get_id.return_value = "val-123"

        # Create a mock RequestValidationError
        mock_exc = MagicMock(spec=RequestValidationError)
        mock_exc.errors.return_value = [
            {
                "loc": ["body", "name"],
                "msg": "field required",
                "type": "value_error.missing",
            },
            {
                "loc": ["body", "email"],
                "msg": "invalid email",
                "type": "value_error.email",
            },
        ]

        response = await validation_exception_handler(mock_request, mock_exc)

        assert response.status_code == 422
        import json

        body = json.loads(response.body)
        assert body["error"] == "ValidationError"
        assert len(body["detail"]) == 2
        assert body["detail"][0]["loc"] == ["body", "name"]
        assert body["detail"][0]["msg"] == "field required"


class TestGenericExceptionHandler:
    """Tests for generic_exception_handler."""

    @pytest.fixture
    def mock_request(self):
        """Create mock request."""
        mock = MagicMock()
        mock.url.path = "/api/action"
        return mock

    @pytest.mark.asyncio
    @patch("api.exceptions.handlers.get_correlation_id")
    async def test_handles_generic_exception(self, mock_get_id, mock_request):
        """Test handling of generic Exception."""
        mock_get_id.return_value = "gen-123"
        exc = Exception("Something went wrong")

        response = await generic_exception_handler(mock_request, exc)

        assert response.status_code == 500
        import json

        body = json.loads(response.body)
        assert body["error"] == "InternalServerError"
        # Should not expose internal error details
        assert "Something went wrong" not in body["detail"]
        assert "unexpected error" in body["detail"].lower()

    @pytest.mark.asyncio
    @patch("api.exceptions.handlers.get_correlation_id")
    async def test_includes_correlation_id(self, mock_get_id, mock_request):
        """Test that correlation ID is included in response."""
        mock_get_id.return_value = "gen-456"
        exc = RuntimeError("Runtime failure")

        response = await generic_exception_handler(mock_request, exc)

        import json

        body = json.loads(response.body)
        assert body["correlation_id"] == "gen-456"
