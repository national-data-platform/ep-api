# tests/test_delete_organization_and_datasets.py
"""Tests for delete_organization_and_datasets service."""

import pytest
from unittest.mock import MagicMock, patch

from ckanapi import NotFound, ValidationError

from api.services.organization_services.delete_organization_and_datasets import (
    delete_organization_and_datasets,
)


class TestDeleteOrganizationAndDatasets:
    """Tests for delete_organization_and_datasets service."""

    @patch("api.services.organization_services.delete_organization_and_datasets.ckan_settings")
    def test_delete_success_with_datasets(self, mock_ckan_settings):
        """Test successful deletion of organization with datasets."""
        mock_ckan = MagicMock()
        mock_ckan.action.package_search.return_value = {
            "results": [
                {"id": "dataset-1"},
                {"id": "dataset-2"},
                {"id": "dataset-3"},
            ]
        }
        mock_ckan_settings.ckan = mock_ckan

        result = delete_organization_and_datasets("test-org")

        assert "test-org" in result
        assert "deleted" in result.lower()
        assert mock_ckan.action.package_delete.call_count == 3
        mock_ckan.action.organization_delete.assert_called_once_with(id="test-org")

    @patch("api.services.organization_services.delete_organization_and_datasets.ckan_settings")
    def test_delete_success_no_datasets(self, mock_ckan_settings):
        """Test successful deletion of organization with no datasets."""
        mock_ckan = MagicMock()
        mock_ckan.action.package_search.return_value = {"results": []}
        mock_ckan_settings.ckan = mock_ckan

        result = delete_organization_and_datasets("empty-org")

        assert "empty-org" in result
        assert "deleted" in result.lower()
        mock_ckan.action.package_delete.assert_not_called()
        mock_ckan.action.organization_delete.assert_called_once_with(id="empty-org")

    @patch("api.services.organization_services.delete_organization_and_datasets.ckan_settings")
    def test_delete_validation_error(self, mock_ckan_settings):
        """Test validation error during deletion."""
        mock_ckan = MagicMock()
        mock_ckan.action.package_search.return_value = {"results": []}
        validation_error = ValidationError({"organization": ["Invalid organization"]})
        mock_ckan.action.organization_delete.side_effect = validation_error
        mock_ckan_settings.ckan = mock_ckan

        with pytest.raises(Exception) as exc_info:
            delete_organization_and_datasets("invalid-org")

        assert "Validation error" in str(exc_info.value)

    @patch("api.services.organization_services.delete_organization_and_datasets.ckan_settings")
    def test_delete_not_found_error(self, mock_ckan_settings):
        """Test organization not found error."""
        mock_ckan = MagicMock()
        mock_ckan.action.package_search.return_value = {"results": []}
        mock_ckan.action.organization_delete.side_effect = NotFound()
        mock_ckan_settings.ckan = mock_ckan

        with pytest.raises(Exception) as exc_info:
            delete_organization_and_datasets("nonexistent-org")

        assert "not found" in str(exc_info.value).lower()

    @patch("api.services.organization_services.delete_organization_and_datasets.ckan_settings")
    def test_delete_generic_error(self, mock_ckan_settings):
        """Test generic error during deletion."""
        mock_ckan = MagicMock()
        mock_ckan.action.package_search.side_effect = Exception("Database error")
        mock_ckan_settings.ckan = mock_ckan

        with pytest.raises(Exception) as exc_info:
            delete_organization_and_datasets("test-org")

        assert "Error deleting organization" in str(exc_info.value)

    @patch("api.services.organization_services.delete_organization_and_datasets.ckan_settings")
    def test_delete_dataset_error(self, mock_ckan_settings):
        """Test error when deleting a dataset."""
        mock_ckan = MagicMock()
        mock_ckan.action.package_search.return_value = {
            "results": [{"id": "dataset-1"}]
        }
        mock_ckan.action.package_delete.side_effect = Exception("Delete failed")
        mock_ckan_settings.ckan = mock_ckan

        with pytest.raises(Exception) as exc_info:
            delete_organization_and_datasets("test-org")

        assert "Error deleting organization" in str(exc_info.value)

    @patch("api.services.organization_services.delete_organization_and_datasets.ckan_settings")
    def test_delete_many_datasets(self, mock_ckan_settings):
        """Test deletion of organization with many datasets."""
        mock_ckan = MagicMock()
        datasets = [{"id": f"dataset-{i}"} for i in range(100)]
        mock_ckan.action.package_search.return_value = {"results": datasets}
        mock_ckan_settings.ckan = mock_ckan

        result = delete_organization_and_datasets("big-org")

        assert "big-org" in result
        assert mock_ckan.action.package_delete.call_count == 100
        mock_ckan.action.organization_delete.assert_called_once()
