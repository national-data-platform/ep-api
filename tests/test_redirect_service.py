# tests/test_redirect_service.py
"""Tests for redirect_service (get_service_url)."""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock

from api.services.service_services.redirect_service import get_service_url


class TestGetServiceUrl:
    """Tests for get_service_url."""

    @pytest.mark.asyncio
    @patch("api.services.service_services.redirect_service.search_datasource")
    async def test_get_service_url_success_from_resource(self, mock_search):
        """Test successful service URL retrieval from resource."""
        mock_resource = MagicMock()
        mock_resource.format = "service"
        mock_resource.url = "http://service.example.com/api"

        mock_dataset = MagicMock()
        mock_dataset.resources = [mock_resource]
        mock_dataset.extras = {}

        mock_search.return_value = [mock_dataset]

        url, error = await get_service_url("my-service")

        assert url == "http://service.example.com/api"
        assert error is None
        mock_search.assert_called_once_with(
            dataset_name="my-service",
            owner_org="services",
            server="local",
        )

    @pytest.mark.asyncio
    @patch("api.services.service_services.redirect_service.search_datasource")
    async def test_get_service_url_success_from_extras(self, mock_search):
        """Test successful service URL retrieval from extras."""
        mock_resource = MagicMock()
        mock_resource.format = "csv"  # Not a service format
        mock_resource.url = "http://data.example.com/data.csv"

        mock_dataset = MagicMock()
        mock_dataset.resources = [mock_resource]
        mock_dataset.extras = {"service_url": "http://service.example.com/api"}

        mock_search.return_value = [mock_dataset]

        url, error = await get_service_url("my-service")

        assert url == "http://service.example.com/api"
        assert error is None

    @pytest.mark.asyncio
    @patch("api.services.service_services.redirect_service.search_datasource")
    async def test_get_service_url_not_found(self, mock_search):
        """Test service not found."""
        mock_search.return_value = []

        url, error = await get_service_url("nonexistent-service")

        assert url is None
        assert "not found" in error.lower()

    @pytest.mark.asyncio
    @patch("api.services.service_services.redirect_service.search_datasource")
    async def test_get_service_url_no_url_in_resources_or_extras(self, mock_search):
        """Test when service URL is not in resources or extras."""
        mock_resource = MagicMock()
        mock_resource.format = "csv"
        mock_resource.url = "http://data.example.com/data.csv"

        mock_dataset = MagicMock()
        mock_dataset.resources = [mock_resource]
        mock_dataset.extras = {}

        mock_search.return_value = [mock_dataset]

        url, error = await get_service_url("my-service")

        assert url is None
        assert "URL not found" in error

    @pytest.mark.asyncio
    @patch("api.services.service_services.redirect_service.search_datasource")
    async def test_get_service_url_with_server_parameter(self, mock_search):
        """Test service URL retrieval with different server."""
        mock_resource = MagicMock()
        mock_resource.format = "service"
        mock_resource.url = "http://global-service.example.com/api"

        mock_dataset = MagicMock()
        mock_dataset.resources = [mock_resource]
        mock_dataset.extras = {}

        mock_search.return_value = [mock_dataset]

        url, error = await get_service_url("my-service", server="global")

        assert url == "http://global-service.example.com/api"
        assert error is None
        mock_search.assert_called_once_with(
            dataset_name="my-service",
            owner_org="services",
            server="global",
        )

    @pytest.mark.asyncio
    @patch("api.services.service_services.redirect_service.search_datasource")
    async def test_get_service_url_exception_no_scheme(self, mock_search):
        """Test exception handling for No scheme supplied error."""
        mock_search.side_effect = Exception("No scheme supplied")

        url, error = await get_service_url("my-service")

        assert url is None
        assert "not configured or unreachable" in error

    @pytest.mark.asyncio
    @patch("api.services.service_services.redirect_service.search_datasource")
    async def test_get_service_url_generic_exception(self, mock_search):
        """Test generic exception handling."""
        mock_search.side_effect = Exception("Database connection failed")

        url, error = await get_service_url("my-service")

        assert url is None
        assert "Error retrieving service" in error
        assert "Database connection failed" in error

    @pytest.mark.asyncio
    @patch("api.services.service_services.redirect_service.search_datasource")
    async def test_get_service_url_case_insensitive_format(self, mock_search):
        """Test that service format check is case-insensitive."""
        mock_resource = MagicMock()
        mock_resource.format = "SERVICE"  # Uppercase
        mock_resource.url = "http://service.example.com/api"

        mock_dataset = MagicMock()
        mock_dataset.resources = [mock_resource]
        mock_dataset.extras = {}

        mock_search.return_value = [mock_dataset]

        url, error = await get_service_url("my-service")

        assert url == "http://service.example.com/api"
        assert error is None

    @pytest.mark.asyncio
    @patch("api.services.service_services.redirect_service.search_datasource")
    async def test_get_service_url_multiple_resources(self, mock_search):
        """Test service URL retrieval with multiple resources."""
        mock_resource1 = MagicMock()
        mock_resource1.format = "csv"
        mock_resource1.url = "http://data.example.com/data.csv"

        mock_resource2 = MagicMock()
        mock_resource2.format = "service"
        mock_resource2.url = "http://service.example.com/api"

        mock_resource3 = MagicMock()
        mock_resource3.format = "json"
        mock_resource3.url = "http://data.example.com/data.json"

        mock_dataset = MagicMock()
        mock_dataset.resources = [mock_resource1, mock_resource2, mock_resource3]
        mock_dataset.extras = {}

        mock_search.return_value = [mock_dataset]

        url, error = await get_service_url("my-service")

        # Should return the first service format resource
        assert url == "http://service.example.com/api"
        assert error is None

    @pytest.mark.asyncio
    @patch("api.services.service_services.redirect_service.search_datasource")
    async def test_get_service_url_empty_extras(self, mock_search):
        """Test when extras is None."""
        mock_resource = MagicMock()
        mock_resource.format = "csv"
        mock_resource.url = "http://data.example.com/data.csv"

        mock_dataset = MagicMock()
        mock_dataset.resources = [mock_resource]
        mock_dataset.extras = None

        mock_search.return_value = [mock_dataset]

        url, error = await get_service_url("my-service")

        assert url is None
        assert "URL not found" in error

    @pytest.mark.asyncio
    @patch("api.services.service_services.redirect_service.search_datasource")
    async def test_get_service_url_resource_format_none(self, mock_search):
        """Test when resource format is None."""
        mock_resource = MagicMock()
        mock_resource.format = None
        mock_resource.url = "http://data.example.com/data"

        mock_dataset = MagicMock()
        mock_dataset.resources = [mock_resource]
        mock_dataset.extras = {"service_url": "http://service.example.com/api"}

        mock_search.return_value = [mock_dataset]

        url, error = await get_service_url("my-service")

        # Should fall back to extras
        assert url == "http://service.example.com/api"
        assert error is None
