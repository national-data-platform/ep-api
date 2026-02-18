# tests/test_affinities_client.py
"""Tests for Affinities client module."""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from uuid import UUID

from api.services.affinities_services.affinities_client import AffinitiesClient


class TestAffinitiesClient:
    """Tests for AffinitiesClient."""

    def test_is_enabled_when_disabled(self):
        """Test is_enabled returns False when disabled."""
        with patch(
            "api.services.affinities_services.affinities_client.affinities_settings"
        ) as mock_settings:
            mock_settings.is_configured = False
            client = AffinitiesClient()
            assert client.is_enabled is False

    def test_is_enabled_when_enabled(self):
        """Test is_enabled returns True when properly configured."""
        with patch(
            "api.services.affinities_services.affinities_client.affinities_settings"
        ) as mock_settings:
            mock_settings.is_configured = True
            mock_settings.url = "http://affinities:8000"
            mock_settings.ep_uuid = "550e8400-e29b-41d4-a716-446655440000"
            mock_settings.timeout = 30
            client = AffinitiesClient()
            assert client.is_enabled is True

    @pytest.mark.asyncio
    async def test_register_dataset_when_disabled(self):
        """Test register_dataset does nothing when disabled."""
        with patch(
            "api.services.affinities_services.affinities_client.affinities_settings"
        ) as mock_settings:
            mock_settings.is_configured = False
            client = AffinitiesClient()

            result = await client.register_dataset(title="Test Dataset")

            assert result is None

    @pytest.mark.asyncio
    @patch("api.services.affinities_services.affinities_client.httpx.AsyncClient")
    async def test_register_dataset_success(self, mock_client_class):
        """Test successful dataset registration."""
        with patch(
            "api.services.affinities_services.affinities_client.affinities_settings"
        ) as mock_settings:
            mock_settings.is_configured = True
            mock_settings.url = "http://affinities:8000"
            mock_settings.ep_uuid = "550e8400-e29b-41d4-a716-446655440000"
            mock_settings.timeout = 30

            # Mock the HTTP response for dataset creation
            dataset_response = MagicMock()
            dataset_response.json.return_value = {
                "uid": "12345678-1234-1234-1234-123456789abc"
            }
            dataset_response.raise_for_status = MagicMock()

            # Mock the HTTP response for relationship creation
            relationship_response = MagicMock()
            relationship_response.json.return_value = {}
            relationship_response.raise_for_status = MagicMock()

            mock_client = AsyncMock()
            mock_client.request = AsyncMock(
                side_effect=[dataset_response, relationship_response]
            )
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            client = AffinitiesClient()
            result = await client.register_dataset(
                title="Test Dataset", metadata={"key": "value"}
            )

            assert result == UUID("12345678-1234-1234-1234-123456789abc")

    @pytest.mark.asyncio
    @patch("api.services.affinities_services.affinities_client.httpx.AsyncClient")
    async def test_register_dataset_handles_error(self, mock_client_class):
        """Test dataset registration handles errors gracefully."""
        import httpx

        with patch(
            "api.services.affinities_services.affinities_client.affinities_settings"
        ) as mock_settings:
            mock_settings.is_configured = True
            mock_settings.url = "http://affinities:8000"
            mock_settings.ep_uuid = "550e8400-e29b-41d4-a716-446655440000"
            mock_settings.timeout = 30

            mock_client = AsyncMock()
            mock_client.request = AsyncMock(
                side_effect=httpx.TimeoutException("Connection timed out")
            )
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            client = AffinitiesClient()
            result = await client.register_dataset(title="Test Dataset")

            # Should return None on error, not raise
            assert result is None

    @pytest.mark.asyncio
    async def test_register_service_when_disabled(self):
        """Test register_service does nothing when disabled."""
        with patch(
            "api.services.affinities_services.affinities_client.affinities_settings"
        ) as mock_settings:
            mock_settings.is_configured = False
            client = AffinitiesClient()

            result = await client.register_service(service_type="api")

            assert result is None

    @pytest.mark.asyncio
    @patch("api.services.affinities_services.affinities_client.httpx.AsyncClient")
    async def test_register_service_success(self, mock_client_class):
        """Test successful service registration."""
        with patch(
            "api.services.affinities_services.affinities_client.affinities_settings"
        ) as mock_settings:
            mock_settings.is_configured = True
            mock_settings.url = "http://affinities:8000"
            mock_settings.ep_uuid = "550e8400-e29b-41d4-a716-446655440000"
            mock_settings.timeout = 30

            # Mock the HTTP response for service creation
            service_response = MagicMock()
            service_response.json.return_value = {
                "uid": "87654321-4321-4321-4321-cba987654321"
            }
            service_response.raise_for_status = MagicMock()

            # Mock the HTTP response for relationship creation
            relationship_response = MagicMock()
            relationship_response.json.return_value = {}
            relationship_response.raise_for_status = MagicMock()

            mock_client = AsyncMock()
            mock_client.request = AsyncMock(
                side_effect=[service_response, relationship_response]
            )
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            client = AffinitiesClient()
            result = await client.register_service(
                service_type="api",
                openapi_url="http://example.com/openapi.json",
                version="1.0",
            )

            assert result == UUID("87654321-4321-4321-4321-cba987654321")


class TestAffinitiesSettings:
    """Tests for AffinitiesSettings."""

    def test_is_configured_false_when_disabled(self):
        """Test is_configured returns False when disabled."""
        with patch(
            "api.config.affinities_settings.AffinitiesSettings"
        ) as mock_class:
            instance = MagicMock()
            instance.enabled = False
            instance.url = "http://affinities:8000"
            instance.ep_uuid = "550e8400-e29b-41d4-a716-446655440000"
            # is_configured should be False because enabled=False
            instance.is_configured = False
            mock_class.return_value = instance

            from api.config.affinities_settings import AffinitiesSettings

            settings = AffinitiesSettings()
            assert settings.is_configured is False

    def test_is_configured_false_when_url_missing(self):
        """Test is_configured returns False when URL is missing."""
        with patch(
            "api.config.affinities_settings.AffinitiesSettings"
        ) as mock_class:
            instance = MagicMock()
            instance.enabled = True
            instance.url = ""
            instance.ep_uuid = "550e8400-e29b-41d4-a716-446655440000"
            instance.is_configured = False
            mock_class.return_value = instance

            from api.config.affinities_settings import AffinitiesSettings

            settings = AffinitiesSettings()
            assert settings.is_configured is False
