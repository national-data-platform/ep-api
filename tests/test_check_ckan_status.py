# tests/test_check_ckan_status.py
"""
Tests for check_ckan_status service.
"""
import pytest
from unittest.mock import MagicMock, patch
from ckanapi import NotFound

from api.services.status_services.check_ckan_status import check_ckan_status


class TestCheckCkanStatus:
    """Test cases for check_ckan_status function."""

    @patch("api.services.status_services.check_ckan_status.ckan_settings")
    def test_check_ckan_status_local_active(self, mock_ckan_settings):
        """Test checking local CKAN status when active."""
        mock_ckan = MagicMock()
        mock_ckan.action.status_show.return_value = {"version": "2.9"}
        mock_ckan_settings.ckan = mock_ckan
        mock_ckan_settings.ckan_url = "http://localhost:5000"
        mock_ckan_settings.ckan_api_key = "test-key"

        result = check_ckan_status(local=True)

        assert result is True
        mock_ckan.action.status_show.assert_called_once()

    @patch("api.services.status_services.check_ckan_status.ckan_settings")
    def test_check_ckan_status_global_active(self, mock_ckan_settings):
        """Test checking global CKAN status when active."""
        mock_ckan = MagicMock()
        mock_ckan.action.status_show.return_value = {"version": "2.9"}
        mock_ckan_settings.ckan_global = mock_ckan
        mock_ckan_settings.ckan_url = "http://localhost:5000"
        mock_ckan_settings.ckan_api_key = "test-key"

        result = check_ckan_status(local=False)

        assert result is True
        mock_ckan.action.status_show.assert_called_once()

    @patch("api.services.status_services.check_ckan_status.ckan_settings")
    def test_check_ckan_status_local_not_found(self, mock_ckan_settings):
        """Test checking local CKAN when endpoint not found."""
        mock_ckan = MagicMock()
        mock_ckan.action.status_show.side_effect = NotFound()
        mock_ckan_settings.ckan = mock_ckan
        mock_ckan_settings.ckan_url = "http://localhost:5000"
        mock_ckan_settings.ckan_api_key = "test-key"

        result = check_ckan_status(local=True)

        assert result is False

    @patch("api.services.status_services.check_ckan_status.ckan_settings")
    def test_check_ckan_status_empty_response(self, mock_ckan_settings):
        """Test checking CKAN with empty response."""
        mock_ckan = MagicMock()
        mock_ckan.action.status_show.return_value = None
        mock_ckan_settings.ckan = mock_ckan
        mock_ckan_settings.ckan_url = "http://localhost:5000"
        mock_ckan_settings.ckan_api_key = "test-key"

        result = check_ckan_status(local=True)

        assert result is False

    @patch("api.services.status_services.check_ckan_status.ckan_settings")
    def test_check_ckan_status_connection_error(self, mock_ckan_settings):
        """Test checking CKAN with connection error."""
        mock_ckan = MagicMock()
        mock_ckan.action.status_show.side_effect = Exception("Connection refused")
        mock_ckan_settings.ckan = mock_ckan
        mock_ckan_settings.ckan_url = "http://localhost:5000"
        mock_ckan_settings.ckan_api_key = "test-key"

        with pytest.raises(Exception) as exc_info:
            check_ckan_status(local=True)

        assert "Error checking CKAN status" in str(exc_info.value)
        assert "Connection refused" in str(exc_info.value)

    @patch("api.services.status_services.check_ckan_status.ckan_settings")
    def test_check_ckan_status_default_is_local(self, mock_ckan_settings):
        """Test that default parameter is local=True."""
        mock_ckan = MagicMock()
        mock_ckan.action.status_show.return_value = {"status": "ok"}
        mock_ckan_settings.ckan = mock_ckan
        mock_ckan_settings.ckan_url = "http://localhost:5000"
        mock_ckan_settings.ckan_api_key = "test-key"

        result = check_ckan_status()

        assert result is True
        # Should use local ckan
        assert mock_ckan.action.status_show.called
