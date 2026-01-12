# tests/test_redirect_routes.py
"""Tests for redirect routes."""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from fastapi import HTTPException
import httpx


class TestProxyRequest:
    """Tests for proxy_request function."""

    @pytest.fixture
    def mock_request(self):
        """Create a mock request."""
        mock = MagicMock()
        mock.method = "GET"
        mock.url.query = None
        mock.headers.items.return_value = [
            ("accept", "application/json"),
            ("authorization", "Bearer token"),
        ]
        return mock

    @pytest.mark.asyncio
    @patch("api.routes.redirect_routes.service_redirect.httpx.AsyncClient")
    async def test_proxy_request_get_success(self, mock_client_class, mock_request):
        """Test successful GET proxy request."""
        from api.routes.redirect_routes.service_redirect import proxy_request

        mock_headers = MagicMock()
        mock_headers.items.return_value = [("content-type", "application/json")]
        mock_headers.get.return_value = "application/json"

        mock_response = MagicMock()
        mock_response.content = b'{"result": "ok"}'
        mock_response.status_code = 200
        mock_response.headers = mock_headers

        mock_client = AsyncMock()
        mock_client.request.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client_class.return_value = mock_client

        result = await proxy_request(mock_request, "https://api.example.com")

        assert result.status_code == 200
        assert result.body == b'{"result": "ok"}'

    @pytest.mark.asyncio
    @patch("api.routes.redirect_routes.service_redirect.httpx.AsyncClient")
    async def test_proxy_request_with_path(self, mock_client_class, mock_request):
        """Test proxy request with additional path."""
        from api.routes.redirect_routes.service_redirect import proxy_request

        mock_headers = MagicMock()
        mock_headers.items.return_value = []
        mock_headers.get.return_value = None

        mock_response = MagicMock()
        mock_response.content = b"ok"
        mock_response.status_code = 200
        mock_response.headers = mock_headers

        mock_client = AsyncMock()
        mock_client.request.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client_class.return_value = mock_client

        result = await proxy_request(
            mock_request, "https://api.example.com/", "/users/123"
        )

        assert result.status_code == 200
        call_args = mock_client.request.call_args
        assert "/users/123" in call_args[1]["url"]

    @pytest.mark.asyncio
    @patch("api.routes.redirect_routes.service_redirect.httpx.AsyncClient")
    async def test_proxy_request_with_query(self, mock_client_class, mock_request):
        """Test proxy request with query parameters."""
        from api.routes.redirect_routes.service_redirect import proxy_request

        mock_request.url.query = "param=value&other=test"

        mock_headers = MagicMock()
        mock_headers.items.return_value = []
        mock_headers.get.return_value = None

        mock_response = MagicMock()
        mock_response.content = b"ok"
        mock_response.status_code = 200
        mock_response.headers = mock_headers

        mock_client = AsyncMock()
        mock_client.request.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client_class.return_value = mock_client

        result = await proxy_request(mock_request, "https://api.example.com")

        assert result.status_code == 200
        call_args = mock_client.request.call_args
        assert "param=value" in call_args[1]["url"]

    @pytest.mark.asyncio
    @patch("api.routes.redirect_routes.service_redirect.httpx.AsyncClient")
    async def test_proxy_request_post_with_body(self, mock_client_class, mock_request):
        """Test POST proxy request with body."""
        from api.routes.redirect_routes.service_redirect import proxy_request

        mock_request.method = "POST"
        mock_request.body = AsyncMock(return_value=b'{"data": "test"}')

        mock_headers = MagicMock()
        mock_headers.items.return_value = []
        mock_headers.get.return_value = None

        mock_response = MagicMock()
        mock_response.content = b"created"
        mock_response.status_code = 201
        mock_response.headers = mock_headers

        mock_client = AsyncMock()
        mock_client.request.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client_class.return_value = mock_client

        result = await proxy_request(mock_request, "https://api.example.com")

        assert result.status_code == 201

    @pytest.mark.asyncio
    @patch("api.routes.redirect_routes.service_redirect.httpx.AsyncClient")
    async def test_proxy_request_timeout(self, mock_client_class, mock_request):
        """Test proxy request timeout."""
        from api.routes.redirect_routes.service_redirect import proxy_request

        mock_client = AsyncMock()
        mock_client.request.side_effect = httpx.TimeoutException("timeout")
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client_class.return_value = mock_client

        with pytest.raises(HTTPException) as exc_info:
            await proxy_request(mock_request, "https://api.example.com")

        assert exc_info.value.status_code == 504
        assert "timed out" in exc_info.value.detail

    @pytest.mark.asyncio
    @patch("api.routes.redirect_routes.service_redirect.httpx.AsyncClient")
    async def test_proxy_request_connect_error(self, mock_client_class, mock_request):
        """Test proxy request connection error."""
        from api.routes.redirect_routes.service_redirect import proxy_request

        mock_client = AsyncMock()
        mock_client.request.side_effect = httpx.ConnectError("connection refused")
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client_class.return_value = mock_client

        with pytest.raises(HTTPException) as exc_info:
            await proxy_request(mock_request, "https://api.example.com")

        assert exc_info.value.status_code == 502
        assert "Unable to connect" in exc_info.value.detail

    @pytest.mark.asyncio
    @patch("api.routes.redirect_routes.service_redirect.httpx.AsyncClient")
    async def test_proxy_request_generic_error(self, mock_client_class, mock_request):
        """Test proxy request generic error."""
        from api.routes.redirect_routes.service_redirect import proxy_request

        mock_client = AsyncMock()
        mock_client.request.side_effect = Exception("Something went wrong")
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client_class.return_value = mock_client

        with pytest.raises(HTTPException) as exc_info:
            await proxy_request(mock_request, "https://api.example.com")

        assert exc_info.value.status_code == 502
        assert "Error communicating" in exc_info.value.detail

    @pytest.mark.asyncio
    @patch("api.routes.redirect_routes.service_redirect.httpx.AsyncClient")
    async def test_proxy_request_filters_headers(self, mock_client_class, mock_request):
        """Test that proxy request filters excluded headers."""
        from api.routes.redirect_routes.service_redirect import proxy_request

        mock_request.headers.items.return_value = [
            ("accept", "application/json"),
            ("host", "original-host.com"),  # Should be excluded
            ("connection", "keep-alive"),  # Should be excluded
            ("content-type", "application/json"),
        ]

        mock_headers = MagicMock()
        mock_headers.items.return_value = []
        mock_headers.get.return_value = None

        mock_response = MagicMock()
        mock_response.content = b"ok"
        mock_response.status_code = 200
        mock_response.headers = mock_headers

        mock_client = AsyncMock()
        mock_client.request.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client_class.return_value = mock_client

        await proxy_request(mock_request, "https://api.example.com")

        call_args = mock_client.request.call_args
        forwarded_headers = call_args[1]["headers"]
        assert "host" not in forwarded_headers
        assert "connection" not in forwarded_headers


class TestProxyToServiceFunctional:
    """Tests for proxy_to_service_functional endpoint."""

    @pytest.mark.asyncio
    @patch("api.routes.redirect_routes.service_redirect.proxy_request")
    @patch("api.routes.redirect_routes.service_redirect.get_service_url")
    async def test_proxy_success(self, mock_get_url, mock_proxy):
        """Test successful proxy to service."""
        from api.routes.redirect_routes.service_redirect import (
            proxy_to_service_functional,
        )

        mock_get_url.return_value = ("https://api.example.com", None)
        mock_proxy.return_value = MagicMock(status_code=200)

        request = MagicMock()
        result = await proxy_to_service_functional("my-service", request)

        assert result.status_code == 200
        mock_proxy.assert_called_once()

    @pytest.mark.asyncio
    @patch("api.routes.redirect_routes.service_redirect.get_service_url")
    async def test_proxy_service_not_found(self, mock_get_url):
        """Test proxy with service not found."""
        from api.routes.redirect_routes.service_redirect import (
            proxy_to_service_functional,
        )

        mock_get_url.return_value = (None, "Service not found")

        with pytest.raises(HTTPException) as exc_info:
            await proxy_to_service_functional("missing-service", MagicMock())

        assert exc_info.value.status_code == 404


class TestProxyToServiceWithPath:
    """Tests for proxy_to_service_with_path_functional endpoint."""

    @pytest.mark.asyncio
    @patch("api.routes.redirect_routes.service_redirect.proxy_request")
    @patch("api.routes.redirect_routes.service_redirect.get_service_url")
    async def test_proxy_with_path_success(self, mock_get_url, mock_proxy):
        """Test successful proxy with path."""
        from api.routes.redirect_routes.service_redirect import (
            proxy_to_service_with_path_functional,
        )

        mock_get_url.return_value = ("https://api.example.com", None)
        mock_proxy.return_value = MagicMock(status_code=200)

        request = MagicMock()
        result = await proxy_to_service_with_path_functional(
            "my-service", "users/123", request
        )

        assert result.status_code == 200
        mock_proxy.assert_called_once_with(
            request, "https://api.example.com", "users/123"
        )

    @pytest.mark.asyncio
    @patch("api.routes.redirect_routes.service_redirect.get_service_url")
    async def test_proxy_with_path_not_found(self, mock_get_url):
        """Test proxy with path service not found."""
        from api.routes.redirect_routes.service_redirect import (
            proxy_to_service_with_path_functional,
        )

        mock_get_url.return_value = (None, "Service not found")

        with pytest.raises(HTTPException) as exc_info:
            await proxy_to_service_with_path_functional(
                "missing-service", "users", MagicMock()
            )

        assert exc_info.value.status_code == 404


class TestDocsOnlyEndpoints:
    """Tests for docs-only endpoints."""

    @pytest.mark.asyncio
    async def test_redirect_docs_only(self):
        """Test docs-only endpoint raises 501."""
        from api.routes.redirect_routes.service_redirect import redirect_docs_only

        with pytest.raises(HTTPException) as exc_info:
            await redirect_docs_only("my-service")

        assert exc_info.value.status_code == 501
        assert "documentation-only" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_redirect_with_path_docs_only(self):
        """Test docs-only with path endpoint raises 501."""
        from api.routes.redirect_routes.service_redirect import (
            redirect_with_path_docs_only,
        )

        with pytest.raises(HTTPException) as exc_info:
            await redirect_with_path_docs_only("my-service", "users/123")

        assert exc_info.value.status_code == 501
        assert "documentation-only" in exc_info.value.detail
