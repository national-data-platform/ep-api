# tests/test_full_metrics.py
"""Tests for full_metrics service."""

import pytest
from unittest.mock import patch, MagicMock

from api.services.status_services.full_metrics import get_full_metrics


class TestGetFullMetrics:
    """Tests for get_full_metrics function."""

    @patch("api.services.status_services.full_metrics.get_status")
    @patch("api.services.status_services.full_metrics.get_system_metrics")
    @patch("api.services.status_services.full_metrics.get_public_ip")
    def test_get_full_metrics_success(self, mock_ip, mock_system, mock_status):
        """Test successful metrics retrieval."""
        mock_ip.return_value = "1.2.3.4"
        mock_system.return_value = (25.0, 4.0, 16.0, 100.0, 500.0)
        mock_status.return_value = {
            "api_version": "1.0.0",
            "backend_connected": True,
        }

        result = get_full_metrics()

        assert result["public_ip"] == "1.2.3.4"
        assert result["cpu"] == "25.0%"
        assert result["memory"] == "4.0GB/16.0GB"
        assert result["disk"] == "100.0GB/500.0GB"
        assert result["services"]["api_version"] == "1.0.0"

    @patch("api.services.status_services.full_metrics.get_status")
    @patch("api.services.status_services.full_metrics.get_system_metrics")
    @patch("api.services.status_services.full_metrics.get_public_ip")
    def test_get_full_metrics_high_usage(self, mock_ip, mock_system, mock_status):
        """Test metrics with high resource usage."""
        mock_ip.return_value = "192.168.1.1"
        mock_system.return_value = (95.5, 15.8, 16.0, 480.2, 500.0)
        mock_status.return_value = {}

        result = get_full_metrics()

        assert result["cpu"] == "95.5%"
        assert result["memory"] == "15.8GB/16.0GB"
        assert result["disk"] == "480.2GB/500.0GB"

    @patch("api.services.status_services.full_metrics.get_status")
    @patch("api.services.status_services.full_metrics.get_system_metrics")
    @patch("api.services.status_services.full_metrics.get_public_ip")
    def test_get_full_metrics_ip_error(self, mock_ip, mock_system, mock_status):
        """Test metrics when IP retrieval fails."""
        mock_ip.return_value = "Error retrieving IP"
        mock_system.return_value = (10.0, 2.0, 8.0, 50.0, 100.0)
        mock_status.return_value = {}

        result = get_full_metrics()

        assert "Error" in result["public_ip"]
