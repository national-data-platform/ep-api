# tests/test_add_datasource.py

from unittest.mock import MagicMock, patch

import pytest

from api.services.datasource_services.add_datasource import (
    RESERVED_KEYS,
    add_datasource,
)


class TestAddDatasource:
    """Test cases for the add_datasource service function."""

    def test_add_datasource_success_minimal_params(self):
        """Test successful datasource creation with minimal parameters."""
        with patch(
            "api.services.datasource_services.add_datasource.ckan_settings"
        ) as mock_ckan_settings:
            # Mock CKAN instance
            mock_ckan = MagicMock()
            mock_ckan_settings.ckan = mock_ckan

            # Mock successful dataset creation
            mock_dataset = {"id": "test-dataset-id-123"}
            mock_ckan.action.package_create.return_value = mock_dataset

            # Mock successful resource creation
            mock_ckan.action.resource_create.return_value = {
                "id": "test-resource-id-123"
            }

            result = add_datasource(
                dataset_name="test_dataset",
                dataset_title="Test Dataset",
                owner_org="test_org",
                resource_url="https://example.com/data.csv",
                resource_name="test_resource",
            )

            assert result == "test-dataset-id-123"

            # Verify dataset creation was called with correct parameters
            mock_ckan.action.package_create.assert_called_once_with(
                name="test_dataset",
                title="Test Dataset",
                owner_org="test_org",
                notes="",
            )

            # Verify resource creation was called with correct parameters
            mock_ckan.action.resource_create.assert_called_once_with(
                package_id="test-dataset-id-123",
                url="https://example.com/data.csv",
                name="test_resource",
                description="",
                format=None,
            )

    def test_add_datasource_success_with_all_params(self):
        """Test successful datasource creation with all parameters."""
        with patch(
            "api.services.datasource_services.add_datasource.ckan_settings"
        ) as mock_ckan_settings:
            mock_ckan = MagicMock()
            mock_ckan_settings.ckan = mock_ckan

            mock_dataset = {"id": "test-dataset-id-456"}
            mock_ckan.action.package_create.return_value = mock_dataset
            mock_ckan.action.resource_create.return_value = {
                "id": "test-resource-id-456"
            }

            extras = {"custom_field": "custom_value", "category": "finance"}

            result = add_datasource(
                dataset_name="full_test_dataset",
                dataset_title="Full Test Dataset",
                owner_org="test_org_full",
                resource_url="https://example.com/full_data.json",
                resource_name="full_test_resource",
                dataset_description="This is a full test dataset",
                resource_description="This is a full test resource",
                resource_format="JSON",
                extras=extras,
            )

            assert result == "test-dataset-id-456"

            # Verify dataset creation with extras
            expected_dataset_dict = {
                "name": "full_test_dataset",
                "title": "Full Test Dataset",
                "owner_org": "test_org_full",
                "notes": "This is a full test dataset",
                "extras": [
                    {"key": "custom_field", "value": "custom_value"},
                    {"key": "category", "value": "finance"},
                ],
            }
            mock_ckan.action.package_create.assert_called_once_with(
                **expected_dataset_dict
            )

            # Verify resource creation with all parameters
            mock_ckan.action.resource_create.assert_called_once_with(
                package_id="test-dataset-id-456",
                url="https://example.com/full_data.json",
                name="full_test_resource",
                description="This is a full test resource",
                format="JSON",
            )

    def test_add_datasource_success_with_empty_extras(self):
        """Test successful datasource creation with empty extras dict."""
        with patch(
            "api.services.datasource_services.add_datasource.ckan_settings"
        ) as mock_ckan_settings:
            mock_ckan = MagicMock()
            mock_ckan_settings.ckan = mock_ckan

            mock_dataset = {"id": "test-dataset-id-789"}
            mock_ckan.action.package_create.return_value = mock_dataset
            mock_ckan.action.resource_create.return_value = {
                "id": "test-resource-id-789"
            }

            result = add_datasource(
                dataset_name="empty_extras_dataset",
                dataset_title="Empty Extras Dataset",
                owner_org="test_org",
                resource_url="https://example.com/data.csv",
                resource_name="test_resource",
                extras={},
            )

            assert result == "test-dataset-id-789"

            # Should not include extras in dataset creation when empty
            mock_ckan.action.package_create.assert_called_once_with(
                name="empty_extras_dataset",
                title="Empty Extras Dataset",
                owner_org="test_org",
                notes="",
            )

    def test_add_datasource_invalid_extras_type(self):
        """Test validation error when extras is not a dict or None."""
        with pytest.raises(ValueError, match="Extras must be a dictionary or None."):
            add_datasource(
                dataset_name="test_dataset",
                dataset_title="Test Dataset",
                owner_org="test_org",
                resource_url="https://example.com/data.csv",
                resource_name="test_resource",
                extras="invalid_extras",  # Should be dict or None
            )

    def test_add_datasource_invalid_extras_list(self):
        """Test validation error when extras is a list."""
        with pytest.raises(ValueError, match="Extras must be a dictionary or None."):
            add_datasource(
                dataset_name="test_dataset",
                dataset_title="Test Dataset",
                owner_org="test_org",
                resource_url="https://example.com/data.csv",
                resource_name="test_resource",
                extras=["invalid", "extras"],
            )

    def test_add_datasource_reserved_keys_error(self):
        """Test KeyError when extras contains reserved keys."""
        reserved_extras = {"name": "reserved_name", "custom_field": "valid_value"}

        with pytest.raises(KeyError, match="Extras contain reserved keys:"):
            add_datasource(
                dataset_name="test_dataset",
                dataset_title="Test Dataset",
                owner_org="test_org",
                resource_url="https://example.com/data.csv",
                resource_name="test_resource",
                extras=reserved_extras,
            )

    def test_add_datasource_multiple_reserved_keys_error(self):
        """Test KeyError when extras contains multiple reserved keys."""
        reserved_extras = {
            "name": "reserved_name",
            "title": "reserved_title",
            "id": "reserved_id",
            "custom_field": "valid_value",
        }

        with pytest.raises(KeyError, match="Extras contain reserved keys:"):
            add_datasource(
                dataset_name="test_dataset",
                dataset_title="Test Dataset",
                owner_org="test_org",
                resource_url="https://example.com/data.csv",
                resource_name="test_resource",
                extras=reserved_extras,
            )

    def test_add_datasource_dataset_creation_error(self):
        """Test exception handling when dataset creation fails."""
        with patch(
            "api.services.datasource_services.add_datasource.ckan_settings"
        ) as mock_ckan_settings:
            mock_ckan = MagicMock()
            mock_ckan_settings.ckan = mock_ckan

            # Mock dataset creation failure
            mock_ckan.action.package_create.side_effect = Exception("CKAN API error")

            with pytest.raises(
                Exception, match="Error creating dataset: CKAN API error"
            ):
                add_datasource(
                    dataset_name="test_dataset",
                    dataset_title="Test Dataset",
                    owner_org="test_org",
                    resource_url="https://example.com/data.csv",
                    resource_name="test_resource",
                )

    def test_add_datasource_resource_creation_error(self):
        """Test exception handling when resource creation fails."""
        with patch(
            "api.services.datasource_services.add_datasource.ckan_settings"
        ) as mock_ckan_settings:
            mock_ckan = MagicMock()
            mock_ckan_settings.ckan = mock_ckan

            # Mock successful dataset creation
            mock_dataset = {"id": "test-dataset-id-999"}
            mock_ckan.action.package_create.return_value = mock_dataset

            # Mock resource creation failure
            mock_ckan.action.resource_create.side_effect = Exception(
                "Resource creation failed"
            )

            with pytest.raises(
                Exception, match="Error creating resource: Resource creation failed"
            ):
                add_datasource(
                    dataset_name="test_dataset",
                    dataset_title="Test Dataset",
                    owner_org="test_org",
                    resource_url="https://example.com/data.csv",
                    resource_name="test_resource",
                )

    def test_add_datasource_dataset_without_id(self):
        """Test handling when dataset creation returns without ID (edge case)."""
        with patch(
            "api.services.datasource_services.add_datasource.ckan_settings"
        ) as mock_ckan_settings:
            mock_ckan = MagicMock()
            mock_ckan_settings.ckan = mock_ckan

            # Mock dataset creation returning empty dict or None ID
            mock_dataset = {"name": "test_dataset"}  # No 'id' field
            mock_ckan.action.package_create.return_value = mock_dataset

            with pytest.raises(Exception, match="Error creating dataset: 'id'"):
                add_datasource(
                    dataset_name="test_dataset",
                    dataset_title="Test Dataset",
                    owner_org="test_org",
                    resource_url="https://example.com/data.csv",
                    resource_name="test_resource",
                )

    def test_add_datasource_dataset_with_none_id(self):
        """Test handling when dataset creation returns None ID."""
        with patch(
            "api.services.datasource_services.add_datasource.ckan_settings"
        ) as mock_ckan_settings:
            mock_ckan = MagicMock()
            mock_ckan_settings.ckan = mock_ckan

            # Mock dataset creation returning None ID
            mock_dataset = {"id": None}
            mock_ckan.action.package_create.return_value = mock_dataset

            with pytest.raises(Exception, match="Unknown error occurred"):
                add_datasource(
                    dataset_name="test_dataset",
                    dataset_title="Test Dataset",
                    owner_org="test_org",
                    resource_url="https://example.com/data.csv",
                    resource_name="test_resource",
                )

    def test_add_datasource_dataset_with_empty_string_id(self):
        """Test handling when dataset creation returns empty string ID."""
        with patch(
            "api.services.datasource_services.add_datasource.ckan_settings"
        ) as mock_ckan_settings:
            mock_ckan = MagicMock()
            mock_ckan_settings.ckan = mock_ckan

            # Mock dataset creation returning empty string ID
            mock_dataset = {"id": ""}
            mock_ckan.action.package_create.return_value = mock_dataset

            with pytest.raises(Exception, match="Unknown error occurred"):
                add_datasource(
                    dataset_name="test_dataset",
                    dataset_title="Test Dataset",
                    owner_org="test_org",
                    resource_url="https://example.com/data.csv",
                    resource_name="test_resource",
                )

    def test_reserved_keys_constant(self):
        """Test that RESERVED_KEYS contains expected values."""
        expected_keys = {
            "name",
            "title",
            "owner_org",
            "notes",
            "id",
            "resources",
            "collection",
        }
        assert RESERVED_KEYS == expected_keys

    def test_add_datasource_with_none_extras_explicit(self):
        """Test datasource creation with explicitly None extras."""
        with patch(
            "api.services.datasource_services.add_datasource.ckan_settings"
        ) as mock_ckan_settings:
            mock_ckan = MagicMock()
            mock_ckan_settings.ckan = mock_ckan

            mock_dataset = {"id": "test-dataset-id-none"}
            mock_ckan.action.package_create.return_value = mock_dataset
            mock_ckan.action.resource_create.return_value = {
                "id": "test-resource-id-none"
            }

            result = add_datasource(
                dataset_name="none_extras_dataset",
                dataset_title="None Extras Dataset",
                owner_org="test_org",
                resource_url="https://example.com/data.csv",
                resource_name="test_resource",
                extras=None,
            )

            assert result == "test-dataset-id-none"

            # Should not include extras in dataset creation when None
            mock_ckan.action.package_create.assert_called_once_with(
                name="none_extras_dataset",
                title="None Extras Dataset",
                owner_org="test_org",
                notes="",
            )
