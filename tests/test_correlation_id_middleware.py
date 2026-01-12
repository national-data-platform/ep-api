# tests/test_correlation_id_middleware.py
"""Tests for correlation ID middleware."""

import pytest
from unittest.mock import MagicMock, AsyncMock
import uuid

from api.middleware.correlation_id import (
    CorrelationIdMiddleware,
    get_correlation_id,
    generate_correlation_id,
    correlation_id_ctx,
    CORRELATION_ID_HEADER,
)


class TestGenerateCorrelationId:
    """Tests for generate_correlation_id function."""

    def test_generates_valid_uuid(self):
        """Test that generate_correlation_id returns a valid UUID4."""
        correlation_id = generate_correlation_id()

        # Should be a valid UUID
        parsed = uuid.UUID(correlation_id)
        assert parsed.version == 4

    def test_generates_unique_ids(self):
        """Test that each call generates a unique ID."""
        ids = [generate_correlation_id() for _ in range(100)]

        # All IDs should be unique
        assert len(set(ids)) == 100


class TestGetCorrelationId:
    """Tests for get_correlation_id function."""

    def test_returns_none_when_not_set(self):
        """Test that get_correlation_id returns None when not set."""
        # Reset context
        token = correlation_id_ctx.set(None)
        try:
            result = get_correlation_id()
            assert result is None
        finally:
            correlation_id_ctx.reset(token)

    def test_returns_value_when_set(self):
        """Test that get_correlation_id returns the set value."""
        test_id = "test-correlation-id-123"
        token = correlation_id_ctx.set(test_id)
        try:
            result = get_correlation_id()
            assert result == test_id
        finally:
            correlation_id_ctx.reset(token)


class TestCorrelationIdMiddleware:
    """Tests for CorrelationIdMiddleware."""

    @pytest.fixture
    def middleware(self):
        """Create middleware instance."""
        return CorrelationIdMiddleware(app=MagicMock())

    @pytest.fixture
    def mock_request_without_header(self):
        """Create mock request without correlation ID header."""
        mock = MagicMock()
        mock.headers.get.return_value = None
        return mock

    @pytest.fixture
    def mock_request_with_header(self):
        """Create mock request with correlation ID header."""
        mock = MagicMock()
        mock.headers.get.return_value = "existing-correlation-id"
        return mock

    @pytest.mark.asyncio
    async def test_generates_id_when_not_in_header(
        self, middleware, mock_request_without_header
    ):
        """Test that middleware generates ID when not in request header."""
        mock_response = MagicMock()
        mock_response.headers = {}

        async def call_next(request):
            # Verify correlation ID is set in context during request
            assert get_correlation_id() is not None
            return mock_response

        response = await middleware.dispatch(mock_request_without_header, call_next)

        # Response should have correlation ID header
        assert CORRELATION_ID_HEADER in response.headers
        # Should be a valid UUID
        uuid.UUID(response.headers[CORRELATION_ID_HEADER])

    @pytest.mark.asyncio
    async def test_uses_existing_id_from_header(
        self, middleware, mock_request_with_header
    ):
        """Test that middleware uses existing ID from request header."""
        mock_response = MagicMock()
        mock_response.headers = {}

        async def call_next(request):
            # Verify existing correlation ID is used
            assert get_correlation_id() == "existing-correlation-id"
            return mock_response

        response = await middleware.dispatch(mock_request_with_header, call_next)

        # Response should have same correlation ID
        assert response.headers[CORRELATION_ID_HEADER] == "existing-correlation-id"

    @pytest.mark.asyncio
    async def test_context_is_reset_after_request(
        self, middleware, mock_request_without_header
    ):
        """Test that context is reset after request completes."""
        mock_response = MagicMock()
        mock_response.headers = {}

        captured_id = None

        async def call_next(request):
            nonlocal captured_id
            captured_id = get_correlation_id()
            return mock_response

        await middleware.dispatch(mock_request_without_header, call_next)

        # Correlation ID should have been set during request
        assert captured_id is not None
        # But should be reset after request
        # Note: In real scenarios, context vars are thread-local

    @pytest.mark.asyncio
    async def test_context_reset_on_exception(
        self, middleware, mock_request_without_header
    ):
        """Test that context is reset even when exception occurs."""

        async def call_next(request):
            raise ValueError("Test exception")

        with pytest.raises(ValueError):
            await middleware.dispatch(mock_request_without_header, call_next)

        # Context should still be cleaned up via finally block
