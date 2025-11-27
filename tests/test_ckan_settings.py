# tests/test_ckan_settings.py
"""
Tests for CKAN settings configuration.
"""
import pytest
from unittest.mock import patch
from api.config.ckan_settings import Settings


class TestCKANSettings:
    """Test cases for CKAN settings properties."""

    def test_ckan_property_with_api_key(self):
        """Test ckan property returns RemoteCKAN with API key."""
        settings = Settings(ckan_url="http://test-ckan.com", ckan_api_key="test-key")
        ckan_client = settings.ckan

        # Should have the URL and API key set
        assert ckan_client.address == "http://test-ckan.com"
        assert ckan_client.apikey == "test-key"

    def test_ckan_no_api_key_property(self):
        """Test ckan_no_api_key property returns RemoteCKAN without API key."""
        settings = Settings(ckan_url="http://test-ckan.com")
        ckan_client = settings.ckan_no_api_key

        # Should have the URL but no API key
        assert ckan_client.address == "http://test-ckan.com"
        assert ckan_client.apikey is None

    def test_ckan_global_property(self):
        """Test ckan_global property returns RemoteCKAN for global catalog."""
        settings = Settings(ckan_global_url="http://global-ckan.com")
        ckan_client = settings.ckan_global

        assert ckan_client.address == "http://global-ckan.com"

    def test_pre_ckan_property_with_http_url(self):
        """Test pre_ckan property with HTTP URL."""
        settings = Settings(
            pre_ckan_url="http://pre-ckan.com",
            pre_ckan_api_key="pre-key"
        )
        ckan_client = settings.pre_ckan

        assert ckan_client.address == "http://pre-ckan.com"
        assert ckan_client.apikey == "pre-key"

    def test_pre_ckan_property_with_https_url(self):
        """Test pre_ckan property with HTTPS URL."""
        settings = Settings(
            pre_ckan_url="https://pre-ckan.com",
            pre_ckan_api_key="pre-key"
        )
        ckan_client = settings.pre_ckan

        assert ckan_client.address == "https://pre-ckan.com"
        assert ckan_client.apikey == "pre-key"

    def test_pre_ckan_property_without_scheme(self):
        """Test pre_ckan property prepends http:// if no scheme provided."""
        settings = Settings(
            pre_ckan_url="pre-ckan.com",
            pre_ckan_api_key="pre-key"
        )
        ckan_client = settings.pre_ckan

        # Should prepend http://
        assert ckan_client.address == "http://pre-ckan.com"
        assert ckan_client.apikey == "pre-key"

    def test_pre_ckan_no_api_key_with_http_url(self):
        """Test pre_ckan_no_api_key property with HTTP URL."""
        settings = Settings(pre_ckan_url="http://pre-ckan.com")
        ckan_client = settings.pre_ckan_no_api_key

        assert ckan_client.address == "http://pre-ckan.com"
        assert ckan_client.apikey is None

    def test_pre_ckan_no_api_key_without_scheme(self):
        """Test pre_ckan_no_api_key property prepends http:// if no scheme provided."""
        settings = Settings(pre_ckan_url="pre-ckan.com")
        ckan_client = settings.pre_ckan_no_api_key

        # Should prepend http://
        assert ckan_client.address == "http://pre-ckan.com"
        assert ckan_client.apikey is None

    def test_settings_custom_values(self):
        """Test Settings with custom values."""
        settings = Settings(
            ckan_local_enabled=True,
            ckan_url="http://custom.com",
            ckan_api_key="custom-key",
            ckan_global_url="http://custom-global.com",
            pre_ckan_enabled=True,
            pre_ckan_url="http://custom-pre.com",
            pre_ckan_api_key="custom-pre-key"
        )

        assert settings.ckan_local_enabled is True
        assert settings.ckan_url == "http://custom.com"
        assert settings.ckan_api_key == "custom-key"
        assert settings.ckan_global_url == "http://custom-global.com"
        assert settings.pre_ckan_enabled is True
        assert settings.pre_ckan_url == "http://custom-pre.com"
        assert settings.pre_ckan_api_key == "custom-pre-key"
