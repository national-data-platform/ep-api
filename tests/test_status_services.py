# tests/test_status_services.py
"""Tests for status services (check_api_status, system_metrics)."""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock

from api.services.status_services.check_api_status import (
    check_backend_connection,
    check_pre_ckan_connection,
    check_s3_connection,
    get_status,
)
from api.services.status_services.system_metrics import (
    get_public_ip,
    get_system_metrics,
    get_num_datasets,
    get_num_services,
    get_services_titles,
)


class TestCheckBackendConnection:
    """Tests for check_backend_connection."""

    @patch("api.services.status_services.check_api_status.catalog_settings")
    def test_backend_connection_success(self, mock_catalog_settings):
        """Test successful backend connection check."""
        mock_repo = MagicMock()
        mock_repo.check_health.return_value = True
        mock_catalog_settings.local_catalog = mock_repo

        result = check_backend_connection()

        assert result is True
        mock_repo.check_health.assert_called_once()

    @patch("api.services.status_services.check_api_status.catalog_settings")
    def test_backend_connection_failure(self, mock_catalog_settings):
        """Test failed backend connection check."""
        mock_repo = MagicMock()
        mock_repo.check_health.return_value = False
        mock_catalog_settings.local_catalog = mock_repo

        result = check_backend_connection()

        assert result is False

    @patch("api.services.status_services.check_api_status.catalog_settings")
    def test_backend_connection_exception(self, mock_catalog_settings):
        """Test backend connection check with exception."""
        mock_repo = MagicMock()
        mock_repo.check_health.side_effect = Exception("Connection error")
        mock_catalog_settings.local_catalog = mock_repo

        result = check_backend_connection()

        assert result is False


class TestCheckPreCkanConnection:
    """Tests for check_pre_ckan_connection."""

    @patch("api.services.status_services.check_api_status.catalog_settings")
    def test_pre_ckan_connection_success(self, mock_catalog_settings):
        """Test successful PreCKAN connection check."""
        mock_repo = MagicMock()
        mock_repo.check_health.return_value = True
        mock_catalog_settings.pre_catalog = mock_repo

        result = check_pre_ckan_connection()

        assert result is True

    @patch("api.services.status_services.check_api_status.catalog_settings")
    def test_pre_ckan_connection_failure(self, mock_catalog_settings):
        """Test failed PreCKAN connection check."""
        mock_repo = MagicMock()
        mock_repo.check_health.return_value = False
        mock_catalog_settings.pre_catalog = mock_repo

        result = check_pre_ckan_connection()

        assert result is False

    @patch("api.services.status_services.check_api_status.catalog_settings")
    def test_pre_ckan_connection_exception(self, mock_catalog_settings):
        """Test PreCKAN connection check with exception."""
        mock_repo = MagicMock()
        mock_repo.check_health.side_effect = Exception("Connection error")
        mock_catalog_settings.pre_catalog = mock_repo

        result = check_pre_ckan_connection()

        assert result is False


class TestCheckS3Connection:
    """Tests for check_s3_connection."""

    @patch("api.services.status_services.check_api_status.minio_client")
    def test_s3_connection_success(self, mock_minio_client):
        """Test successful S3 connection check."""
        mock_minio_client.test_connection.return_value = True

        result = check_s3_connection()

        assert result is True

    @patch("api.services.status_services.check_api_status.minio_client")
    def test_s3_connection_failure(self, mock_minio_client):
        """Test failed S3 connection check."""
        mock_minio_client.test_connection.return_value = False

        result = check_s3_connection()

        assert result is False

    @patch("api.services.status_services.check_api_status.minio_client")
    def test_s3_connection_exception(self, mock_minio_client):
        """Test S3 connection check with exception."""
        mock_minio_client.test_connection.side_effect = Exception("S3 error")

        result = check_s3_connection()

        assert result is False


class TestGetStatus:
    """Tests for get_status."""

    @patch("api.services.status_services.check_api_status.check_s3_connection")
    @patch("api.services.status_services.check_api_status.check_pre_ckan_connection")
    @patch("api.services.status_services.check_api_status.check_backend_connection")
    @patch("api.services.status_services.check_api_status.s3_settings")
    @patch("api.services.status_services.check_api_status.kafka_settings")
    @patch("api.services.status_services.check_api_status.ckan_settings")
    @patch("api.services.status_services.check_api_status.catalog_settings")
    @patch("api.services.status_services.check_api_status.swagger_settings")
    def test_get_status_basic(
        self,
        mock_swagger,
        mock_catalog,
        mock_ckan,
        mock_kafka,
        mock_s3,
        mock_backend,
        mock_pre_ckan,
        mock_s3_conn,
    ):
        """Test basic status response."""
        mock_swagger.swagger_version = "1.0.0"
        mock_swagger.organization = "test-org"
        mock_swagger.ep_name = "Test EP"
        mock_swagger.enable_group_based_access = False
        mock_swagger.use_jupyterlab = False
        mock_swagger.auth_api_url = "http://auth.example.com"
        mock_swagger.metrics_endpoint = "http://metrics.example.com"
        mock_swagger.metrics_interval_seconds = 60
        mock_swagger.is_public = True
        mock_catalog.local_catalog_backend = "mongodb"
        mock_ckan.pre_ckan_enabled = False
        mock_kafka.kafka_connection = False
        mock_s3.s3_enabled = False
        mock_backend.return_value = True

        result = get_status()

        assert result["api_version"] == "1.0.0"
        assert result["organization"] == "test-org"
        assert result["ep_name"] == "Test EP"
        assert result["backend_connected"] is True

    @patch("api.services.status_services.check_api_status.check_s3_connection")
    @patch("api.services.status_services.check_api_status.check_pre_ckan_connection")
    @patch("api.services.status_services.check_api_status.check_backend_connection")
    @patch("api.services.status_services.check_api_status.s3_settings")
    @patch("api.services.status_services.check_api_status.kafka_settings")
    @patch("api.services.status_services.check_api_status.ckan_settings")
    @patch("api.services.status_services.check_api_status.catalog_settings")
    @patch("api.services.status_services.check_api_status.swagger_settings")
    def test_get_status_with_pre_ckan(
        self,
        mock_swagger,
        mock_catalog,
        mock_ckan,
        mock_kafka,
        mock_s3,
        mock_backend,
        mock_pre_ckan,
        mock_s3_conn,
    ):
        """Test status with PreCKAN enabled."""
        mock_swagger.swagger_version = "1.0.0"
        mock_swagger.organization = "test-org"
        mock_swagger.ep_name = "Test EP"
        mock_swagger.enable_group_based_access = False
        mock_swagger.use_jupyterlab = False
        mock_swagger.auth_api_url = ""
        mock_swagger.metrics_endpoint = ""
        mock_swagger.metrics_interval_seconds = 60
        mock_swagger.is_public = True
        mock_catalog.local_catalog_backend = "ckan"
        mock_ckan.pre_ckan_enabled = True
        mock_kafka.kafka_connection = False
        mock_s3.s3_enabled = False
        mock_backend.return_value = True
        mock_pre_ckan.return_value = True

        result = get_status()

        assert result["pre_ckan_enabled"] is True
        assert result["pre_ckan_connected"] is True

    @patch("api.services.status_services.check_api_status.check_s3_connection")
    @patch("api.services.status_services.check_api_status.check_pre_ckan_connection")
    @patch("api.services.status_services.check_api_status.check_backend_connection")
    @patch("api.services.status_services.check_api_status.s3_settings")
    @patch("api.services.status_services.check_api_status.kafka_settings")
    @patch("api.services.status_services.check_api_status.ckan_settings")
    @patch("api.services.status_services.check_api_status.catalog_settings")
    @patch("api.services.status_services.check_api_status.swagger_settings")
    def test_get_status_with_kafka(
        self,
        mock_swagger,
        mock_catalog,
        mock_ckan,
        mock_kafka,
        mock_s3,
        mock_backend,
        mock_pre_ckan,
        mock_s3_conn,
    ):
        """Test status with Kafka enabled."""
        mock_swagger.swagger_version = "1.0.0"
        mock_swagger.organization = "test-org"
        mock_swagger.ep_name = "Test EP"
        mock_swagger.enable_group_based_access = False
        mock_swagger.use_jupyterlab = False
        mock_swagger.auth_api_url = ""
        mock_swagger.metrics_endpoint = ""
        mock_swagger.metrics_interval_seconds = 60
        mock_swagger.is_public = True
        mock_catalog.local_catalog_backend = "mongodb"
        mock_ckan.pre_ckan_enabled = False
        mock_kafka.kafka_connection = True
        mock_kafka.kafka_host = "kafka.example.com"
        mock_kafka.kafka_port = 9092
        mock_s3.s3_enabled = False
        mock_backend.return_value = True

        result = get_status()

        assert result["kafka_enabled"] is True
        assert result["kafka_host"] == "kafka.example.com"
        assert result["kafka_port"] == 9092

    @patch("api.services.status_services.check_api_status.check_s3_connection")
    @patch("api.services.status_services.check_api_status.check_pre_ckan_connection")
    @patch("api.services.status_services.check_api_status.check_backend_connection")
    @patch("api.services.status_services.check_api_status.s3_settings")
    @patch("api.services.status_services.check_api_status.kafka_settings")
    @patch("api.services.status_services.check_api_status.ckan_settings")
    @patch("api.services.status_services.check_api_status.catalog_settings")
    @patch("api.services.status_services.check_api_status.swagger_settings")
    def test_get_status_with_jupyterlab(
        self,
        mock_swagger,
        mock_catalog,
        mock_ckan,
        mock_kafka,
        mock_s3,
        mock_backend,
        mock_pre_ckan,
        mock_s3_conn,
    ):
        """Test status with JupyterLab enabled."""
        mock_swagger.swagger_version = "1.0.0"
        mock_swagger.organization = "test-org"
        mock_swagger.ep_name = "Test EP"
        mock_swagger.enable_group_based_access = False
        mock_swagger.use_jupyterlab = True
        mock_swagger.jupyter_url = "http://jupyter.example.com"
        mock_swagger.auth_api_url = ""
        mock_swagger.metrics_endpoint = ""
        mock_swagger.metrics_interval_seconds = 60
        mock_swagger.is_public = True
        mock_catalog.local_catalog_backend = "mongodb"
        mock_ckan.pre_ckan_enabled = False
        mock_kafka.kafka_connection = False
        mock_s3.s3_enabled = False
        mock_backend.return_value = True

        result = get_status()

        assert result["jupyterlab_enabled"] is True
        assert result["jupyterlab_url"] == "http://jupyter.example.com"

    @patch("api.services.status_services.check_api_status.check_s3_connection")
    @patch("api.services.status_services.check_api_status.check_pre_ckan_connection")
    @patch("api.services.status_services.check_api_status.check_backend_connection")
    @patch("api.services.status_services.check_api_status.s3_settings")
    @patch("api.services.status_services.check_api_status.kafka_settings")
    @patch("api.services.status_services.check_api_status.ckan_settings")
    @patch("api.services.status_services.check_api_status.catalog_settings")
    @patch("api.services.status_services.check_api_status.swagger_settings")
    def test_get_status_with_s3(
        self,
        mock_swagger,
        mock_catalog,
        mock_ckan,
        mock_kafka,
        mock_s3,
        mock_backend,
        mock_pre_ckan,
        mock_s3_conn,
    ):
        """Test status with S3 enabled."""
        mock_swagger.swagger_version = "1.0.0"
        mock_swagger.organization = "test-org"
        mock_swagger.ep_name = "Test EP"
        mock_swagger.enable_group_based_access = False
        mock_swagger.use_jupyterlab = False
        mock_swagger.auth_api_url = ""
        mock_swagger.metrics_endpoint = ""
        mock_swagger.metrics_interval_seconds = 60
        mock_swagger.is_public = True
        mock_catalog.local_catalog_backend = "mongodb"
        mock_ckan.pre_ckan_enabled = False
        mock_kafka.kafka_connection = False
        mock_s3.s3_enabled = True
        mock_backend.return_value = True
        mock_s3_conn.return_value = True

        result = get_status()

        assert result["s3_enabled"] is True
        assert result["s3_connected"] is True


class TestGetPublicIp:
    """Tests for get_public_ip."""

    @patch("api.services.status_services.system_metrics.requests")
    def test_get_public_ip_success(self, mock_requests):
        """Test successful public IP retrieval."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"ip": "1.2.3.4"}
        mock_requests.get.return_value = mock_response

        result = get_public_ip()

        assert result == "1.2.3.4"

    @patch("api.services.status_services.system_metrics.requests")
    def test_get_public_ip_error(self, mock_requests):
        """Test public IP retrieval error."""
        mock_requests.get.side_effect = Exception("Network error")
        mock_requests.RequestException = Exception

        result = get_public_ip()

        assert "Error" in result


class TestGetSystemMetrics:
    """Tests for get_system_metrics."""

    @patch("api.services.status_services.system_metrics.psutil")
    def test_get_system_metrics_success(self, mock_psutil):
        """Test successful system metrics retrieval."""
        mock_psutil.cpu_percent.return_value = 25.0

        mock_memory = MagicMock()
        mock_memory.used = 4 * (1024**3)  # 4 GB
        mock_memory.total = 16 * (1024**3)  # 16 GB
        mock_psutil.virtual_memory.return_value = mock_memory

        mock_disk = MagicMock()
        mock_disk.used = 100 * (1024**3)  # 100 GB
        mock_disk.total = 500 * (1024**3)  # 500 GB
        mock_psutil.disk_usage.return_value = mock_disk

        cpu, mem_used, mem_total, disk_used, disk_total = get_system_metrics()

        assert cpu == 25.0
        assert mem_used == 4.0
        assert mem_total == 16.0
        assert disk_used == 100.0
        assert disk_total == 500.0


class TestGetNumDatasets:
    """Tests for get_num_datasets."""

    def test_get_num_datasets_success(self):
        """Test successful dataset count."""
        mock_repo = MagicMock()
        mock_repo.package_search.return_value = {"count": 42}

        result = get_num_datasets(mock_repo)

        assert result == 42
        mock_repo.package_search.assert_called_once_with(q="*:*", rows=0)

    def test_get_num_datasets_error(self):
        """Test dataset count with error."""
        mock_repo = MagicMock()
        mock_repo.package_search.side_effect = Exception("Database error")

        result = get_num_datasets(mock_repo)

        assert result == 0

    def test_get_num_datasets_no_count(self):
        """Test dataset count with missing count field."""
        mock_repo = MagicMock()
        mock_repo.package_search.return_value = {}

        result = get_num_datasets(mock_repo)

        assert result == 0


class TestGetNumServices:
    """Tests for get_num_services."""

    def test_get_num_services_success(self):
        """Test successful service count."""
        mock_repo = MagicMock()
        mock_repo.package_search.return_value = {"count": 10}

        result = get_num_services(mock_repo)

        assert result == 10
        mock_repo.package_search.assert_called_once_with(
            q="*:*", fq="owner_org:services", rows=0
        )

    def test_get_num_services_error(self):
        """Test service count with error."""
        mock_repo = MagicMock()
        mock_repo.package_search.side_effect = Exception("Database error")

        result = get_num_services(mock_repo)

        assert result == 0


class TestGetServicesTitles:
    """Tests for get_services_titles."""

    def test_get_services_titles_success(self):
        """Test successful service titles retrieval."""
        mock_repo = MagicMock()
        mock_repo.package_search.return_value = {
            "results": [
                {"title": "Service 1"},
                {"title": "Service 2"},
                {"title": "Service 3"},
            ]
        }

        result = get_services_titles(mock_repo)

        assert result == ["Service 1", "Service 2", "Service 3"]

    def test_get_services_titles_error(self):
        """Test service titles retrieval with error."""
        mock_repo = MagicMock()
        mock_repo.package_search.side_effect = Exception("Database error")

        result = get_services_titles(mock_repo)

        assert result == []

    def test_get_services_titles_empty(self):
        """Test service titles when no services exist."""
        mock_repo = MagicMock()
        mock_repo.package_search.return_value = {"results": []}

        result = get_services_titles(mock_repo)

        assert result == []

    def test_get_services_titles_missing_title(self):
        """Test service titles with missing title field."""
        mock_repo = MagicMock()
        mock_repo.package_search.return_value = {
            "results": [
                {"title": "Service 1"},
                {"name": "service-no-title"},
                {"title": "Service 3"},
            ]
        }

        result = get_services_titles(mock_repo)

        assert result == ["Service 1", "", "Service 3"]
