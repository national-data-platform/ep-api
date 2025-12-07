"""Tests for DataSpaces details endpoint."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

from api.main import app


client = TestClient(app)


class TestDSpacesDetailsEndpoint:
    """Test suite for /status/dspaces-details endpoint."""

    def test_get_dspaces_details_success(self):
        """Test successful retrieval of DataSpaces details."""
        with patch(
            "api.routes.status_routes.dspaces_details.dspaces_settings"
        ) as mock_settings:
            mock_settings.dspaces_enabled = True
            mock_settings.dspaces_url = "http://localhost:8003"

            response = client.get("/status/dspaces-details")

            assert response.status_code == 200
            data = response.json()
            assert "dspaces_enabled" in data
            assert "dspaces_url" in data
            assert data["dspaces_enabled"] is True
            assert data["dspaces_url"] == "http://localhost:8003"

    def test_get_dspaces_details_disabled(self):
        """Test DataSpaces details when disabled."""
        with patch(
            "api.routes.status_routes.dspaces_details.dspaces_settings"
        ) as mock_settings:
            mock_settings.dspaces_enabled = False
            mock_settings.dspaces_url = ""

            response = client.get("/status/dspaces-details")

            assert response.status_code == 200
            data = response.json()
            assert data["dspaces_enabled"] is False
            assert data["dspaces_url"] == ""

    def test_get_dspaces_details_error_handling(self):
        """Test error handling in DataSpaces details endpoint."""
        with patch(
            "api.routes.status_routes.dspaces_details.dspaces_settings"
        ) as mock_settings:
            # Simulate an error by making property access raise
            type(mock_settings).dspaces_enabled = property(
                lambda self: (_ for _ in ()).throw(Exception("Test error"))
            )

            response = client.get("/status/dspaces-details")

            assert response.status_code == 500
            assert "Error retrieving DataSpaces details" in response.json()["detail"]
