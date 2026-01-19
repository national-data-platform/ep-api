# tests/test_delete_dataset_service.py
"""
Tests for delete_dataset service.
"""

import pytest
from unittest.mock import MagicMock, patch

from api.services.dataset_services.delete_dataset import delete_dataset


class TestDeleteDataset:
    """Test cases for delete_dataset function."""

    @patch("api.services.dataset_services.delete_dataset.catalog_settings")
    def test_delete_dataset_by_name(self, mock_catalog_settings):
        """Test deleting dataset by name."""
        mock_repository = MagicMock()
        mock_repository.package_delete.return_value = None
        mock_catalog_settings.local_catalog = mock_repository

        delete_dataset(dataset_name="test-dataset")

        mock_repository.package_delete.assert_called_once_with(id="test-dataset")

    @patch("api.services.dataset_services.delete_dataset.catalog_settings")
    def test_delete_dataset_by_resource_id(self, mock_catalog_settings):
        """Test deleting dataset by resource_id."""
        mock_repository = MagicMock()
        mock_repository.package_delete.return_value = None
        mock_catalog_settings.local_catalog = mock_repository

        delete_dataset(resource_id="res-123")

        mock_repository.package_delete.assert_called_once_with(id="res-123")

    def test_delete_dataset_with_custom_repository(self):
        """Test deleting dataset with custom repository."""
        mock_repository = MagicMock()
        mock_repository.package_delete.return_value = None

        delete_dataset(dataset_name="my-dataset", repository=mock_repository)

        mock_repository.package_delete.assert_called_once_with(id="my-dataset")

    @patch("api.services.dataset_services.delete_dataset.catalog_settings")
    def test_delete_dataset_no_identifier_raises_error(self, mock_catalog_settings):
        """Test that missing identifier raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            delete_dataset()

        assert "Must provide either dataset_name or resource_id" in str(exc_info.value)

    @patch("api.services.dataset_services.delete_dataset.catalog_settings")
    def test_delete_dataset_both_identifiers_uses_name(self, mock_catalog_settings):
        """Test that dataset_name takes precedence over resource_id."""
        mock_repository = MagicMock()
        mock_repository.package_delete.return_value = None
        mock_catalog_settings.local_catalog = mock_repository

        delete_dataset(dataset_name="dataset-name", resource_id="res-id")

        # Should use dataset_name
        mock_repository.package_delete.assert_called_once_with(id="dataset-name")

    @patch("api.services.dataset_services.delete_dataset.catalog_settings")
    def test_delete_dataset_not_found_error(self, mock_catalog_settings):
        """Test handling of not found error."""
        mock_repository = MagicMock()
        mock_repository.package_delete.side_effect = Exception("Dataset not found")
        mock_catalog_settings.local_catalog = mock_repository

        with pytest.raises(Exception) as exc_info:
            delete_dataset(dataset_name="missing-dataset")

        assert "not found" in str(exc_info.value).lower()

    @patch("api.services.dataset_services.delete_dataset.catalog_settings")
    def test_delete_dataset_generic_error(self, mock_catalog_settings):
        """Test handling of generic errors."""
        mock_repository = MagicMock()
        mock_repository.package_delete.side_effect = Exception("Permission denied")
        mock_catalog_settings.local_catalog = mock_repository

        with pytest.raises(Exception) as exc_info:
            delete_dataset(dataset_name="test-dataset")

        assert "Error deleting dataset" in str(exc_info.value)
        assert "Permission denied" in str(exc_info.value)

    @patch("api.services.dataset_services.delete_dataset.catalog_settings")
    def test_delete_dataset_empty_string_name_raises_error(self, mock_catalog_settings):
        """Test that empty string name raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            delete_dataset(dataset_name="", resource_id="")

        assert "Must provide either dataset_name or resource_id" in str(exc_info.value)

    @patch("api.services.dataset_services.delete_dataset.catalog_settings")
    def test_delete_dataset_none_values_raises_error(self, mock_catalog_settings):
        """Test that None values for both raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            delete_dataset(dataset_name=None, resource_id=None)

        assert "Must provide either dataset_name or resource_id" in str(exc_info.value)
