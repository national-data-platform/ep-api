# tests/test_delete_organization_service.py
"""
Tests for delete_organization service.
"""

import pytest
from unittest.mock import MagicMock, patch

from api.services.organization_services.delete_organization import delete_organization


class TestDeleteOrganization:
    """Test cases for delete_organization function."""

    @patch("api.services.organization_services.delete_organization.catalog_settings")
    def test_delete_organization_with_no_datasets(self, mock_catalog_settings):
        """Test deleting organization with no datasets."""
        mock_repository = MagicMock()
        mock_repository.organization_show.return_value = {
            "id": "org-123",
            "name": "test-org",
        }
        mock_repository.package_search.return_value = {"count": 0, "results": []}
        mock_repository.organization_delete.return_value = None
        mock_repository.organization_purge.return_value = None
        mock_catalog_settings.local_catalog = mock_repository

        delete_organization("test-org")

        mock_repository.organization_show.assert_called_once_with(id="test-org")
        mock_repository.package_search.assert_called_once()
        mock_repository.organization_delete.assert_called_once_with(id="org-123")
        mock_repository.organization_purge.assert_called_once_with(id="org-123")

    @patch("api.services.organization_services.delete_organization.catalog_settings")
    def test_delete_organization_with_datasets(self, mock_catalog_settings):
        """Test deleting organization with associated datasets."""
        mock_repository = MagicMock()
        mock_repository.organization_show.return_value = {
            "id": "org-456",
            "name": "org-with-data",
        }
        mock_repository.package_search.return_value = {
            "count": 2,
            "results": [
                {"id": "dataset-1", "name": "ds1"},
                {"id": "dataset-2", "name": "ds2"},
            ],
        }
        mock_repository.package_delete.return_value = None
        mock_repository.organization_delete.return_value = None
        mock_repository.organization_purge.return_value = None
        mock_catalog_settings.local_catalog = mock_repository

        delete_organization("org-with-data")

        # Verify datasets were deleted
        assert mock_repository.package_delete.call_count == 2
        mock_repository.package_delete.assert_any_call(id="dataset-1")
        mock_repository.package_delete.assert_any_call(id="dataset-2")
        # Verify organization was deleted
        mock_repository.organization_delete.assert_called_once_with(id="org-456")

    def test_delete_organization_with_custom_repository(self):
        """Test deleting organization with custom repository."""
        mock_repository = MagicMock()
        mock_repository.organization_show.return_value = {
            "id": "custom-org",
            "name": "custom",
        }
        mock_repository.package_search.return_value = {"results": []}
        mock_repository.organization_delete.return_value = None
        mock_repository.organization_purge.return_value = None

        delete_organization("custom", repository=mock_repository)

        mock_repository.organization_show.assert_called_once_with(id="custom")
        mock_repository.organization_delete.assert_called_once()

    @patch("api.services.organization_services.delete_organization.catalog_settings")
    def test_delete_organization_not_found(self, mock_catalog_settings):
        """Test deleting non-existent organization."""
        mock_repository = MagicMock()
        mock_repository.organization_show.side_effect = Exception(
            "Organization not found"
        )
        mock_catalog_settings.local_catalog = mock_repository

        with pytest.raises(Exception) as exc_info:
            delete_organization("nonexistent-org")

        assert "Organization not found" in str(exc_info.value)

    @patch("api.services.organization_services.delete_organization.catalog_settings")
    def test_delete_organization_mongodb_no_purge(self, mock_catalog_settings):
        """Test that MongoDB repos without purge don't fail."""
        mock_repository = MagicMock()
        mock_repository.organization_show.return_value = {
            "id": "mongo-org",
            "name": "mongo",
        }
        mock_repository.package_search.return_value = {"results": []}
        mock_repository.organization_delete.return_value = None
        # Simulate MongoDB repo without purge method
        del mock_repository.organization_purge
        mock_catalog_settings.local_catalog = mock_repository

        # Should not raise error even without purge method
        delete_organization("mongo")

        mock_repository.organization_delete.assert_called_once_with(id="mongo-org")

    @patch("api.services.organization_services.delete_organization.catalog_settings")
    def test_delete_organization_search_with_correct_filter(
        self, mock_catalog_settings
    ):
        """Test that package search uses correct filter query."""
        mock_repository = MagicMock()
        mock_repository.organization_show.return_value = {
            "id": "filter-org-id",
            "name": "filter-org",
        }
        mock_repository.package_search.return_value = {"results": []}
        mock_repository.organization_delete.return_value = None
        mock_repository.organization_purge.return_value = None
        mock_catalog_settings.local_catalog = mock_repository

        delete_organization("filter-org")

        # Verify the filter query uses organization ID
        call_args = mock_repository.package_search.call_args
        assert call_args[1]["fq"] == "owner_org:filter-org-id"
        assert call_args[1]["rows"] == 1000

    @patch("api.services.organization_services.delete_organization.catalog_settings")
    def test_delete_organization_generic_error(self, mock_catalog_settings):
        """Test handling of generic errors."""
        mock_repository = MagicMock()
        mock_repository.organization_show.side_effect = Exception("Permission denied")
        mock_catalog_settings.local_catalog = mock_repository

        with pytest.raises(Exception) as exc_info:
            delete_organization("test-org")

        assert "Error deleting organization" in str(exc_info.value)
        assert "Permission denied" in str(exc_info.value)

    @patch("api.services.organization_services.delete_organization.catalog_settings")
    def test_delete_organization_dataset_deletion_order(self, mock_catalog_settings):
        """Test that datasets are deleted before organization."""
        deletion_order = []

        def track_delete(call_type):
            def _delete(*args, **kwargs):
                deletion_order.append(call_type)

            return _delete

        mock_repository = MagicMock()
        mock_repository.organization_show.return_value = {
            "id": "order-org",
            "name": "order",
        }
        mock_repository.package_search.return_value = {"results": [{"id": "ds-1"}]}
        mock_repository.package_delete.side_effect = track_delete("dataset")
        mock_repository.organization_delete.side_effect = track_delete("organization")
        mock_repository.organization_purge.return_value = None
        mock_catalog_settings.local_catalog = mock_repository

        delete_organization("order")

        # Datasets should be deleted before organization
        assert deletion_order[0] == "dataset"
        assert deletion_order[1] == "organization"
