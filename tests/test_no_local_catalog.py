# tests/test_no_local_catalog.py
"""
An Endpoint with no local catalog (LOCAL_CATALOG_BACKEND=none).

The lightest deployment there is: no MongoDB, no CKAN, nothing stored locally.
It authenticates users, searches the global catalog and reports to the
Federation, so it must come up, report itself ready and keep sending metrics
even though there is no catalog to talk to.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from api.config.catalog_settings import CatalogSettings
from api.routes.health_routes.ready import _check_local_catalog
from api.services.status_services.check_api_status import check_backend_connection
from api.tasks.metrics_task import record_system_metrics


class TestCatalogSettings:
    """LOCAL_CATALOG_BACKEND=none as a first-class setting."""

    def test_none_means_there_is_no_local_catalog(self):
        assert CatalogSettings(local_catalog_backend="none").has_local_catalog is False

    def test_case_is_not_significant(self):
        assert CatalogSettings(local_catalog_backend="None").has_local_catalog is False

    @pytest.mark.parametrize("backend", ["ckan", "mongodb"])
    def test_a_real_backend_has_a_local_catalog(self, backend):
        assert CatalogSettings(local_catalog_backend=backend).has_local_catalog is True

    def test_asking_for_the_repository_says_there_is_none(self):
        """
        Callers that ask anyway get an explanation, not a backend-not-supported
        message that reads like a typo in the configuration.
        """
        settings = CatalogSettings(local_catalog_backend="none")

        with pytest.raises(ValueError) as error:
            settings.local_catalog

        assert "no local catalog" in str(error.value).lower()


class TestReadiness:
    """/ready must not report a catalog that was never meant to exist."""

    @patch("api.routes.health_routes.ready.ckan_settings")
    @patch("api.routes.health_routes.ready.catalog_settings")
    def test_no_catalog_is_disabled_not_down(self, mock_catalog, mock_ckan):
        mock_catalog.local_catalog_backend = "none"
        mock_catalog.has_local_catalog = False
        mock_ckan.ckan_local_enabled = False

        result = _check_local_catalog()

        assert result == {"status": "disabled", "backend": "none"}

    @patch("api.routes.health_routes.ready.ckan_settings")
    @patch("api.routes.health_routes.ready.catalog_settings")
    def test_a_disabled_mongodb_catalog_is_not_probed(self, mock_catalog, mock_ckan):
        """
        With the master switch off the local catalog routes are not mounted for
        any backend, so nothing can reach MongoDB. Probing it reported a
        dependency the Endpoint never uses as down, and answered 503.
        """
        mock_catalog.local_catalog_backend = "mongodb"
        mock_catalog.has_local_catalog = True
        mock_ckan.ckan_local_enabled = False

        result = _check_local_catalog()

        assert result["status"] == "disabled"
        assert result["backend"] == "mongodb"
        mock_catalog.local_catalog.check_health.assert_not_called()

    @patch("api.routes.health_routes.ready.ckan_settings")
    @patch("api.routes.health_routes.ready.catalog_settings")
    def test_an_enabled_catalog_is_still_checked(self, mock_catalog, mock_ckan):
        mock_catalog.local_catalog_backend = "mongodb"
        mock_catalog.has_local_catalog = True
        mock_ckan.ckan_local_enabled = True
        mock_catalog.local_catalog.check_health.return_value = True

        result = _check_local_catalog()

        assert result["status"] == "up"
        assert result["backend"] == "mongodb"


class TestStatus:
    """/status reports the backend without trying to connect to nothing."""

    @patch("api.services.status_services.check_api_status.catalog_settings")
    def test_backend_is_reported_disconnected_without_an_attempt(self, mock_catalog):
        mock_catalog.has_local_catalog = False

        assert check_backend_connection() is False
        mock_catalog.local_catalog.check_health.assert_not_called()


class TestMetrics:
    """
    Metrics collection and the catalog counts share one try/except: an
    exception there leaves the payload empty and skips the POST, so an
    Endpoint with no catalog would silently stop reporting to the Federation.
    """

    @pytest.mark.asyncio
    @patch("api.tasks.metrics_task.httpx.AsyncClient")
    @patch("api.tasks.metrics_task.swagger_settings")
    @patch("api.tasks.metrics_task.kafka_settings")
    @patch("api.tasks.metrics_task.s3_settings")
    @patch("api.tasks.metrics_task.ckan_settings")
    @patch("api.tasks.metrics_task.catalog_settings")
    @patch("api.tasks.metrics_task.get_system_metrics")
    @patch("api.tasks.metrics_task.get_public_ip")
    async def test_metrics_are_still_reported_without_a_catalog(
        self,
        mock_ip,
        mock_system,
        mock_catalog,
        mock_ckan,
        mock_s3,
        mock_kafka,
        mock_swagger,
        mock_httpx,
    ):
        mock_ip.return_value = "1.2.3.4"
        mock_system.return_value = (25.0, 4.0, 16.0, 100.0, 500.0)

        # No catalog: the repository is never asked for, so the counts come
        # from nowhere and the report still goes out.
        mock_catalog.has_local_catalog = False

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
        mock_ckan.ckan_url = ""
        mock_ckan.ckan_api_key = ""

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
        payload = mock_client.post.call_args.kwargs["json"]
        assert payload["num_datasets"] == 0
        assert payload["num_services"] == 0
        assert payload["services"] == []
