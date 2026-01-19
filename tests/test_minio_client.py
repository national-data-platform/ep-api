# tests/test_minio_client.py
"""
Tests for MinioClient wrapper.
"""

import pytest
from unittest.mock import MagicMock, patch
from minio.error import S3Error

from api.services.minio_services.minio_client import MinioClient


class TestMinioClientInitialization:
    """Test MinioClient initialization."""

    def test_init_creates_none_client(self):
        """Test that __init__ creates None client."""
        client_wrapper = MinioClient()

        assert client_wrapper._client is None

    @patch("api.services.minio_services.minio_client.s3_settings")
    def test_client_property_not_configured_raises_error(self, mock_settings):
        """Test that accessing client when not configured raises ValueError."""
        mock_settings.is_configured = False

        client_wrapper = MinioClient()

        with pytest.raises(ValueError) as exc_info:
            _ = client_wrapper.client

        assert "not properly configured" in str(exc_info.value)

    @patch("api.services.minio_services.minio_client.Minio")
    @patch("api.services.minio_services.minio_client.s3_settings")
    def test_client_property_creates_client_on_first_access(
        self, mock_settings, mock_minio
    ):
        """Test that client property creates Minio client on first access."""
        mock_settings.is_configured = True
        mock_settings.endpoint = "localhost:9000"
        mock_settings.access_key = "minioadmin"
        mock_settings.secret_key = "minioadmin"
        mock_settings.secure = False
        mock_settings.region = "us-east-1"

        mock_minio_instance = MagicMock()
        mock_minio.return_value = mock_minio_instance

        client_wrapper = MinioClient()
        result = client_wrapper.client

        assert result is mock_minio_instance
        mock_minio.assert_called_once_with(
            endpoint="localhost:9000",
            access_key="minioadmin",
            secret_key="minioadmin",
            secure=False,
            region="us-east-1",
        )

    @patch("api.services.minio_services.minio_client.Minio")
    @patch("api.services.minio_services.minio_client.s3_settings")
    def test_client_property_reuses_existing_client(self, mock_settings, mock_minio):
        """Test that client property reuses existing Minio client."""
        mock_settings.is_configured = True
        mock_settings.endpoint = "localhost:9000"
        mock_settings.access_key = "minioadmin"
        mock_settings.secret_key = "minioadmin"
        mock_settings.secure = False
        mock_settings.region = "us-east-1"

        mock_minio_instance = MagicMock()
        mock_minio.return_value = mock_minio_instance

        client_wrapper = MinioClient()
        result1 = client_wrapper.client
        result2 = client_wrapper.client

        assert result1 is result2
        assert mock_minio.call_count == 1

    @patch("api.services.minio_services.minio_client.Minio")
    @patch("api.services.minio_services.minio_client.s3_settings")
    def test_client_property_initialization_failure(self, mock_settings, mock_minio):
        """Test that client property raises exception on initialization failure."""
        mock_settings.is_configured = True
        mock_minio.side_effect = Exception("Connection failed")

        client_wrapper = MinioClient()

        with pytest.raises(Exception) as exc_info:
            _ = client_wrapper.client

        assert "Connection failed" in str(exc_info.value)


class TestMinioClientTestConnection:
    """Test test_connection method."""

    @patch("api.services.minio_services.minio_client.s3_settings")
    def test_test_connection_success(self, mock_settings):
        """Test successful connection test."""
        mock_settings.is_configured = True

        mock_bucket = MagicMock()
        mock_bucket.name = "test-bucket"

        mock_minio_client = MagicMock()
        mock_minio_client.list_buckets.return_value = [mock_bucket]

        client_wrapper = MinioClient()
        client_wrapper._client = mock_minio_client

        result = client_wrapper.test_connection()

        assert result is True

    @patch("api.services.minio_services.minio_client.s3_settings")
    def test_test_connection_s3_error(self, mock_settings):
        """Test connection test with S3Error."""
        mock_settings.is_configured = True

        from unittest.mock import Mock

        mock_response = Mock()
        mock_response.status = 403
        mock_response.data = b""
        mock_response.headers = {}
        s3_error = S3Error(
            "AccessDenied",
            "Access denied",
            "resource",
            "req_id",
            "host_id",
            mock_response,
        )

        mock_minio_client = MagicMock()
        mock_minio_client.list_buckets.side_effect = s3_error

        client_wrapper = MinioClient()
        client_wrapper._client = mock_minio_client

        result = client_wrapper.test_connection()

        assert result is False

    @patch("api.services.minio_services.minio_client.s3_settings")
    def test_test_connection_unexpected_error(self, mock_settings):
        """Test connection test with unexpected error."""
        mock_settings.is_configured = True

        mock_minio_client = MagicMock()
        mock_minio_client.list_buckets.side_effect = Exception("Network error")

        client_wrapper = MinioClient()
        client_wrapper._client = mock_minio_client

        result = client_wrapper.test_connection()

        assert result is False
