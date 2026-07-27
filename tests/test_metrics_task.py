# tests/test_metrics_task.py
"""Tests for metrics_task background task."""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import asyncio

from api.tasks.metrics_task import record_system_metrics


class TestRecordSystemMetrics:
    """Tests for record_system_metrics function."""

    @pytest.mark.asyncio
    @patch("api.tasks.metrics_task.swagger_settings")
    @patch("api.tasks.metrics_task.kafka_settings")
    @patch("api.tasks.metrics_task.s3_settings")
    @patch("api.tasks.metrics_task.ckan_settings")
    @patch("api.tasks.metrics_task.catalog_settings")
    @patch("api.tasks.metrics_task.get_services_titles")
    @patch("api.tasks.metrics_task.get_num_services")
    @patch("api.tasks.metrics_task.get_num_datasets")
    @patch("api.tasks.metrics_task.get_system_metrics")
    @patch("api.tasks.metrics_task.get_public_ip")
    async def test_record_metrics_single_iteration(
        self,
        mock_ip,
        mock_system,
        mock_datasets,
        mock_services,
        mock_titles,
        mock_catalog,
        mock_ckan,
        mock_s3,
        mock_kafka,
        mock_swagger,
    ):
        """Test single iteration of metrics collection."""
        mock_ip.return_value = "1.2.3.4"
        mock_system.return_value = (25.0, 4.0, 16.0, 100.0, 500.0)
        mock_datasets.return_value = 10
        mock_services.return_value = 5
        mock_titles.return_value = ["Service 1", "Service 2"]

        mock_catalog.local_catalog = MagicMock()
        mock_swagger.swagger_version = "1.0.0"
        mock_swagger.organization = "test-org"
        mock_swagger.ep_name = "Test EP"
        mock_swagger.use_jupyterlab = False
        mock_swagger.is_public = False
        mock_swagger.metrics_interval_seconds = 0.1

        mock_kafka.kafka_connection = False
        mock_s3.s3_enabled = False
        mock_ckan.pre_ckan_enabled = False

        # Run for a short time then cancel
        task = asyncio.create_task(record_system_metrics())
        await asyncio.sleep(0.15)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

        mock_ip.assert_called()
        mock_system.assert_called()

    @pytest.mark.asyncio
    @patch("api.tasks.metrics_task.httpx.AsyncClient")
    @patch("api.tasks.metrics_task.swagger_settings")
    @patch("api.tasks.metrics_task.kafka_settings")
    @patch("api.tasks.metrics_task.s3_settings")
    @patch("api.tasks.metrics_task.ckan_settings")
    @patch("api.tasks.metrics_task.catalog_settings")
    @patch("api.tasks.metrics_task.get_services_titles")
    @patch("api.tasks.metrics_task.get_num_services")
    @patch("api.tasks.metrics_task.get_num_datasets")
    @patch("api.tasks.metrics_task.get_system_metrics")
    @patch("api.tasks.metrics_task.get_public_ip")
    async def test_record_metrics_with_post(
        self,
        mock_ip,
        mock_system,
        mock_datasets,
        mock_services,
        mock_titles,
        mock_catalog,
        mock_ckan,
        mock_s3,
        mock_kafka,
        mock_swagger,
        mock_httpx,
    ):
        """Test metrics posting when public=True."""
        mock_ip.return_value = "1.2.3.4"
        mock_system.return_value = (25.0, 4.0, 16.0, 100.0, 500.0)
        mock_datasets.return_value = 10
        mock_services.return_value = 5
        mock_titles.return_value = []

        mock_catalog.local_catalog = MagicMock()
        mock_swagger.swagger_version = "1.0.0"
        mock_swagger.organization = "test-org"
        mock_swagger.ep_name = "Test EP"
        mock_swagger.use_jupyterlab = False
        mock_swagger.is_public = True
        mock_swagger.metrics_endpoint = "http://metrics.example.com"
        mock_swagger.metrics_interval_seconds = 0.1

        mock_kafka.kafka_connection = False
        mock_s3.s3_enabled = False
        mock_ckan.pre_ckan_enabled = False

        # Mock httpx client
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_httpx.return_value = mock_client

        task = asyncio.create_task(record_system_metrics())
        await asyncio.sleep(0.15)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

        mock_client.post.assert_called()

    @pytest.mark.asyncio
    @patch("api.tasks.metrics_task.swagger_settings")
    @patch("api.tasks.metrics_task.kafka_settings")
    @patch("api.tasks.metrics_task.s3_settings")
    @patch("api.tasks.metrics_task.ckan_settings")
    @patch("api.tasks.metrics_task.catalog_settings")
    @patch("api.tasks.metrics_task.get_services_titles")
    @patch("api.tasks.metrics_task.get_num_services")
    @patch("api.tasks.metrics_task.get_num_datasets")
    @patch("api.tasks.metrics_task.get_system_metrics")
    @patch("api.tasks.metrics_task.get_public_ip")
    async def test_record_metrics_with_jupyterlab(
        self,
        mock_ip,
        mock_system,
        mock_datasets,
        mock_services,
        mock_titles,
        mock_catalog,
        mock_ckan,
        mock_s3,
        mock_kafka,
        mock_swagger,
    ):
        """Test metrics with JupyterLab enabled."""
        mock_ip.return_value = "1.2.3.4"
        mock_system.return_value = (25.0, 4.0, 16.0, 100.0, 500.0)
        mock_datasets.return_value = 10
        mock_services.return_value = 5
        mock_titles.return_value = []

        mock_catalog.local_catalog = MagicMock()
        mock_swagger.swagger_version = "1.0.0"
        mock_swagger.organization = "test-org"
        mock_swagger.ep_name = "Test EP"
        mock_swagger.use_jupyterlab = True
        mock_swagger.jupyter_url = "http://jupyter.example.com"
        mock_swagger.is_public = False
        mock_swagger.metrics_interval_seconds = 0.1

        mock_kafka.kafka_connection = False
        mock_s3.s3_enabled = False
        mock_ckan.pre_ckan_enabled = False

        task = asyncio.create_task(record_system_metrics())
        await asyncio.sleep(0.15)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    @pytest.mark.asyncio
    @patch("api.tasks.metrics_task.swagger_settings")
    @patch("api.tasks.metrics_task.kafka_settings")
    @patch("api.tasks.metrics_task.s3_settings")
    @patch("api.tasks.metrics_task.ckan_settings")
    @patch("api.tasks.metrics_task.catalog_settings")
    @patch("api.tasks.metrics_task.get_services_titles")
    @patch("api.tasks.metrics_task.get_num_services")
    @patch("api.tasks.metrics_task.get_num_datasets")
    @patch("api.tasks.metrics_task.get_system_metrics")
    @patch("api.tasks.metrics_task.get_public_ip")
    async def test_record_metrics_with_kafka(
        self,
        mock_ip,
        mock_system,
        mock_datasets,
        mock_services,
        mock_titles,
        mock_catalog,
        mock_ckan,
        mock_s3,
        mock_kafka,
        mock_swagger,
    ):
        """Test metrics with Kafka enabled."""
        mock_ip.return_value = "1.2.3.4"
        mock_system.return_value = (25.0, 4.0, 16.0, 100.0, 500.0)
        mock_datasets.return_value = 10
        mock_services.return_value = 5
        mock_titles.return_value = []

        mock_catalog.local_catalog = MagicMock()
        mock_swagger.swagger_version = "1.0.0"
        mock_swagger.organization = "test-org"
        mock_swagger.ep_name = "Test EP"
        mock_swagger.use_jupyterlab = False
        mock_swagger.is_public = False
        mock_swagger.metrics_interval_seconds = 0.1

        mock_kafka.kafka_connection = True
        mock_kafka.kafka_host = "kafka.example.com"
        mock_kafka.kafka_port = 9092
        mock_s3.s3_enabled = False
        mock_ckan.pre_ckan_enabled = False

        task = asyncio.create_task(record_system_metrics())
        await asyncio.sleep(0.15)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    @pytest.mark.asyncio
    @patch("api.tasks.metrics_task.swagger_settings")
    @patch("api.tasks.metrics_task.catalog_settings")
    @patch("api.tasks.metrics_task.get_public_ip")
    async def test_record_metrics_collection_error(
        self,
        mock_ip,
        mock_catalog,
        mock_swagger,
    ):
        """Test handling of metrics collection error."""
        mock_ip.side_effect = Exception("Network error")
        mock_swagger.is_public = False
        mock_swagger.metrics_interval_seconds = 0.1

        task = asyncio.create_task(record_system_metrics())
        await asyncio.sleep(0.15)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    @pytest.mark.asyncio
    @patch("api.tasks.metrics_task.httpx.AsyncClient")
    @patch("api.tasks.metrics_task.swagger_settings")
    @patch("api.tasks.metrics_task.kafka_settings")
    @patch("api.tasks.metrics_task.s3_settings")
    @patch("api.tasks.metrics_task.ckan_settings")
    @patch("api.tasks.metrics_task.catalog_settings")
    @patch("api.tasks.metrics_task.get_services_titles")
    @patch("api.tasks.metrics_task.get_num_services")
    @patch("api.tasks.metrics_task.get_num_datasets")
    @patch("api.tasks.metrics_task.get_system_metrics")
    @patch("api.tasks.metrics_task.get_public_ip")
    async def test_record_metrics_post_error(
        self,
        mock_ip,
        mock_system,
        mock_datasets,
        mock_services,
        mock_titles,
        mock_catalog,
        mock_ckan,
        mock_s3,
        mock_kafka,
        mock_swagger,
        mock_httpx,
    ):
        """Test handling of POST error."""
        mock_ip.return_value = "1.2.3.4"
        mock_system.return_value = (25.0, 4.0, 16.0, 100.0, 500.0)
        mock_datasets.return_value = 10
        mock_services.return_value = 5
        mock_titles.return_value = []

        mock_catalog.local_catalog = MagicMock()
        mock_swagger.swagger_version = "1.0.0"
        mock_swagger.organization = "test-org"
        mock_swagger.ep_name = "Test EP"
        mock_swagger.use_jupyterlab = False
        mock_swagger.is_public = True
        mock_swagger.metrics_endpoint = "http://metrics.example.com"
        mock_swagger.metrics_interval_seconds = 0.1

        mock_kafka.kafka_connection = False
        mock_s3.s3_enabled = False
        mock_ckan.pre_ckan_enabled = False

        # Mock httpx client to raise error
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=Exception("Connection refused"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_httpx.return_value = mock_client

        task = asyncio.create_task(record_system_metrics())
        await asyncio.sleep(0.15)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


class TestAddDeploymentMetrics:
    """Tests for add_deployment_metrics — deployment metadata, no secrets."""

    def test_reports_netbird_and_ckan_metadata(self):
        from api.tasks.metrics_task import add_deployment_metrics

        with (
            patch("api.tasks.metrics_task.ckan_settings") as ckan,
            patch.dict(
                "os.environ",
                {
                    "NETBIRD_ENABLED": "true",
                    "NETBIRD_IP": "100.64.0.5",
                    "NETBIRD_GROUP": "ndp",
                },
                clear=False,
            ),
        ):
            ckan.ckan_url = "https://ckan.example.org"
            ckan.ckan_api_key = "a-real-key"
            payload = {}
            add_deployment_metrics(payload)

        assert payload["netbird_enabled"] is True
        assert payload["netbird_ip"] == "100.64.0.5"
        assert payload["netbird_group"] == "ndp"
        assert payload["ckan_url"] == "https://ckan.example.org"
        assert payload["ckan_api_key_configured"] is True

    def test_never_includes_the_api_key_or_a_derivative(self):
        from api.tasks.metrics_task import add_deployment_metrics

        with (
            patch("api.tasks.metrics_task.ckan_settings") as ckan,
            patch.dict(
                "os.environ",
                {"REPORT_CKAN_API_KEY_IN_METRICS": "true"},  # must be ignored
                clear=False,
            ),
        ):
            ckan.ckan_url = "https://ckan.example.org"
            ckan.ckan_api_key = "super-secret-key"
            payload = {}
            add_deployment_metrics(payload)

        serialized = str(payload)
        assert "super-secret-key" not in serialized
        assert "ckan_api_key" not in payload
        assert "ckan_api_key_fingerprint" not in payload
        assert payload["ckan_api_key_configured"] is True

    def test_placeholder_key_counts_as_not_configured(self):
        from api.tasks.metrics_task import add_deployment_metrics

        with (
            patch("api.tasks.metrics_task.ckan_settings") as ckan,
            patch.dict("os.environ", {}, clear=False),
        ):
            ckan.ckan_url = ""
            ckan.ckan_api_key = "your-api-key"
            payload = {}
            add_deployment_metrics(payload)

        assert payload["ckan_api_key_configured"] is False
        assert "ckan_url" not in payload
