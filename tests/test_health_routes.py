# tests/test_health_routes.py

import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from api.main import app


client = TestClient(app)


class TestHealthEndpoint:
    """Tests for the /health endpoint."""

    def test_health_returns_200(self):
        """Test that /health returns HTTP 200."""
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_returns_healthy_status(self):
        """Test that /health returns healthy status."""
        response = client.get("/health")
        data = response.json()
        assert data["status"] == "healthy"

    def test_health_includes_timestamp(self):
        """Test that /health includes a timestamp."""
        response = client.get("/health")
        data = response.json()
        assert "timestamp" in data
        assert data["timestamp"].endswith("Z")


class TestReadyEndpoint:
    """Tests for the /ready endpoint."""

    @patch("api.routes.health_routes.ready._check_local_catalog")
    @patch("api.routes.health_routes.ready._check_pre_ckan")
    @patch("api.routes.health_routes.ready._check_minio")
    @patch("api.routes.health_routes.ready._check_kafka")
    def test_ready_all_healthy(
        self, mock_kafka, mock_minio, mock_pre_ckan, mock_local_catalog
    ):
        """Test /ready returns 200 when all services are healthy."""
        mock_local_catalog.return_value = {"status": "up", "latency_ms": 5}
        mock_pre_ckan.return_value = {"status": "up", "latency_ms": 10}
        mock_minio.return_value = {"status": "up", "latency_ms": 8}
        mock_kafka.return_value = {"status": "disabled"}

        response = client.get("/ready")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    @patch("api.routes.health_routes.ready._check_local_catalog")
    @patch("api.routes.health_routes.ready._check_pre_ckan")
    @patch("api.routes.health_routes.ready._check_minio")
    @patch("api.routes.health_routes.ready._check_kafka")
    def test_ready_all_disabled(
        self, mock_kafka, mock_minio, mock_pre_ckan, mock_local_catalog
    ):
        """Test /ready returns 200 when all services are disabled."""
        mock_local_catalog.return_value = {"status": "disabled"}
        mock_pre_ckan.return_value = {"status": "disabled"}
        mock_minio.return_value = {"status": "disabled"}
        mock_kafka.return_value = {"status": "disabled"}

        response = client.get("/ready")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    @patch("api.routes.health_routes.ready._check_local_catalog")
    @patch("api.routes.health_routes.ready._check_pre_ckan")
    @patch("api.routes.health_routes.ready._check_minio")
    @patch("api.routes.health_routes.ready._check_kafka")
    def test_ready_service_down_returns_503(
        self, mock_kafka, mock_minio, mock_pre_ckan, mock_local_catalog
    ):
        """Test /ready returns 503 when a service is down."""
        mock_local_catalog.return_value = {
            "status": "down",
            "error": "Connection refused",
        }
        mock_pre_ckan.return_value = {"status": "disabled"}
        mock_minio.return_value = {"status": "disabled"}
        mock_kafka.return_value = {"status": "disabled"}

        response = client.get("/ready")
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "unhealthy"

    @patch("api.routes.health_routes.ready._check_local_catalog")
    @patch("api.routes.health_routes.ready._check_pre_ckan")
    @patch("api.routes.health_routes.ready._check_minio")
    @patch("api.routes.health_routes.ready._check_kafka")
    def test_ready_includes_all_checks(
        self, mock_kafka, mock_minio, mock_pre_ckan, mock_local_catalog
    ):
        """Test /ready includes all dependency checks."""
        mock_local_catalog.return_value = {"status": "up", "latency_ms": 5}
        mock_pre_ckan.return_value = {"status": "disabled"}
        mock_minio.return_value = {"status": "up", "latency_ms": 8}
        mock_kafka.return_value = {"status": "disabled"}

        response = client.get("/ready")
        data = response.json()

        assert "checks" in data
        assert "local_catalog" in data["checks"]
        assert "pre_ckan" in data["checks"]
        assert "minio" in data["checks"]
        assert "kafka" in data["checks"]

    @patch("api.routes.health_routes.ready._check_local_catalog")
    @patch("api.routes.health_routes.ready._check_pre_ckan")
    @patch("api.routes.health_routes.ready._check_minio")
    @patch("api.routes.health_routes.ready._check_kafka")
    def test_ready_includes_timestamp(
        self, mock_kafka, mock_minio, mock_pre_ckan, mock_local_catalog
    ):
        """Test /ready includes a timestamp."""
        mock_local_catalog.return_value = {"status": "disabled"}
        mock_pre_ckan.return_value = {"status": "disabled"}
        mock_minio.return_value = {"status": "disabled"}
        mock_kafka.return_value = {"status": "disabled"}

        response = client.get("/ready")
        data = response.json()
        assert "timestamp" in data
        assert data["timestamp"].endswith("Z")


class TestCheckWithLatency:
    """Tests for the _check_with_latency helper."""

    def test_check_with_latency_success(self):
        """Test _check_with_latency with successful check."""
        from api.routes.health_routes.ready import _check_with_latency

        result = _check_with_latency(lambda: True)
        assert result["status"] == "up"
        assert "latency_ms" in result

    def test_check_with_latency_failure(self):
        """Test _check_with_latency with failed check."""
        from api.routes.health_routes.ready import _check_with_latency

        result = _check_with_latency(lambda: False)
        assert result["status"] == "down"
        assert "latency_ms" in result

    def test_check_with_latency_exception(self):
        """Test _check_with_latency with exception."""
        from api.routes.health_routes.ready import _check_with_latency

        def raise_error():
            raise Exception("Test error")

        result = _check_with_latency(raise_error)
        assert result["status"] == "down"
        assert "error" in result
        assert "Test error" in result["error"]


class TestMinioCheck:
    """Tests for MinIO health check."""

    @patch("api.routes.health_routes.ready.s3_settings")
    def test_minio_disabled(self, mock_settings):
        """Test MinIO check when disabled."""
        from api.routes.health_routes.ready import _check_minio

        mock_settings.is_configured = False

        result = _check_minio()
        assert result["status"] == "disabled"

    @patch("api.routes.health_routes.ready.s3_settings")
    @patch("api.services.minio_services.minio_client.minio_client")
    def test_minio_healthy(self, mock_client, mock_settings):
        """Test MinIO check when healthy."""
        from api.routes.health_routes.ready import _check_minio

        mock_settings.is_configured = True
        mock_client.test_connection.return_value = True

        result = _check_minio()
        assert result["status"] == "up"


class TestLocalCatalogCheck:
    """Tests for local catalog health check."""

    @patch("api.routes.health_routes.ready.catalog_settings")
    @patch("api.routes.health_routes.ready.ckan_settings")
    def test_local_catalog_ckan_disabled(self, mock_ckan_settings, mock_catalog):
        """Test local catalog check when CKAN is disabled."""
        from api.routes.health_routes.ready import _check_local_catalog

        mock_catalog.local_catalog_backend = "ckan"
        mock_ckan_settings.ckan_local_enabled = False

        result = _check_local_catalog()
        assert result["status"] == "disabled"
        assert result["backend"] == "ckan"

    @patch("api.routes.health_routes.ready.catalog_settings")
    @patch("api.routes.health_routes.ready.ckan_settings")
    def test_local_catalog_healthy(self, mock_ckan_settings, mock_catalog):
        """Test local catalog check when healthy."""
        from api.routes.health_routes.ready import _check_local_catalog

        mock_catalog.local_catalog_backend = "mongodb"
        mock_repo = MagicMock()
        mock_repo.check_health.return_value = True
        mock_catalog.local_catalog = mock_repo

        result = _check_local_catalog()
        assert result["status"] == "up"
        assert result["backend"] == "mongodb"


class TestPreCkanCheck:
    """Tests for PreCKAN health check."""

    @patch("api.routes.health_routes.ready.ckan_settings")
    def test_pre_ckan_disabled(self, mock_settings):
        """Test PreCKAN check when disabled."""
        from api.routes.health_routes.ready import _check_pre_ckan

        mock_settings.pre_ckan_enabled = False

        result = _check_pre_ckan()
        assert result["status"] == "disabled"

    @patch("api.routes.health_routes.ready.ckan_settings")
    def test_pre_ckan_no_url(self, mock_settings):
        """Test PreCKAN check when URL not configured."""
        from api.routes.health_routes.ready import _check_pre_ckan

        mock_settings.pre_ckan_enabled = True
        mock_settings.pre_ckan_url = ""
        mock_settings.pre_ckan_api_key = "key"

        result = _check_pre_ckan()
        assert result["status"] == "disabled"


class TestKafkaCheck:
    """Tests for Kafka health check."""

    @patch("api.routes.health_routes.ready.kafka_settings")
    def test_kafka_disabled(self, mock_settings):
        """Test Kafka check when disabled."""
        from api.routes.health_routes.ready import _check_kafka

        mock_settings.kafka_connection = False

        result = _check_kafka()
        assert result["status"] == "disabled"
