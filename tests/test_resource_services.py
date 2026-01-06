# tests/test_resource_services.py
"""Tests for resource services (get, patch, delete)."""

import pytest
from unittest.mock import MagicMock, patch

from api.services.dataset_services.get_resource import get_resource
from api.services.dataset_services.patch_resource import patch_resource
from api.services.dataset_services.delete_resource import delete_resource


class TestGetResource:
    """Tests for get_resource service."""

    def test_get_resource_success(self):
        """Test successful resource retrieval."""
        mock_repo = MagicMock()
        mock_repo.resource_show.return_value = {
            "id": "resource-123",
            "name": "test-resource",
            "url": "http://example.com/data.csv",
            "format": "CSV",
        }

        result = get_resource("resource-123", repository=mock_repo)

        assert result["id"] == "resource-123"
        assert result["name"] == "test-resource"
        mock_repo.resource_show.assert_called_once_with(id="resource-123")

    def test_get_resource_not_found(self):
        """Test resource not found error."""
        mock_repo = MagicMock()
        mock_repo.resource_show.side_effect = Exception("Resource not found")

        with pytest.raises(Exception) as exc_info:
            get_resource("nonexistent-id", repository=mock_repo)

        assert "not found" in str(exc_info.value).lower()

    def test_get_resource_generic_error(self):
        """Test generic error handling."""
        mock_repo = MagicMock()
        mock_repo.resource_show.side_effect = Exception("Database connection failed")

        with pytest.raises(Exception) as exc_info:
            get_resource("resource-123", repository=mock_repo)

        assert "Error retrieving resource" in str(exc_info.value)

    @patch("api.services.dataset_services.get_resource.catalog_settings")
    def test_get_resource_uses_default_catalog(self, mock_catalog_settings):
        """Test that default catalog is used when no repository provided."""
        mock_repo = MagicMock()
        mock_repo.resource_show.return_value = {"id": "resource-123"}
        mock_catalog_settings.local_catalog = mock_repo

        result = get_resource("resource-123")

        assert result["id"] == "resource-123"
        mock_repo.resource_show.assert_called_once()


class TestPatchResource:
    """Tests for patch_resource service."""

    def test_patch_resource_all_fields(self):
        """Test patching resource with all fields."""
        mock_repo = MagicMock()
        mock_repo.resource_patch.return_value = {
            "id": "resource-123",
            "name": "updated-name",
            "url": "http://new-url.com/data.csv",
            "description": "Updated description",
            "format": "JSON",
        }

        result = patch_resource(
            resource_id="resource-123",
            name="updated-name",
            url="http://new-url.com/data.csv",
            description="Updated description",
            format="JSON",
            repository=mock_repo,
        )

        assert result["name"] == "updated-name"
        mock_repo.resource_patch.assert_called_once_with(
            id="resource-123",
            name="updated-name",
            url="http://new-url.com/data.csv",
            description="Updated description",
            format="JSON",
        )

    def test_patch_resource_partial_fields(self):
        """Test patching resource with only some fields."""
        mock_repo = MagicMock()
        mock_repo.resource_patch.return_value = {
            "id": "resource-123",
            "name": "updated-name",
        }

        result = patch_resource(
            resource_id="resource-123",
            name="updated-name",
            repository=mock_repo,
        )

        assert result["name"] == "updated-name"
        # Only id and name should be in the call
        mock_repo.resource_patch.assert_called_once_with(
            id="resource-123",
            name="updated-name",
        )

    def test_patch_resource_only_url(self):
        """Test patching only the URL field."""
        mock_repo = MagicMock()
        mock_repo.resource_patch.return_value = {"id": "resource-123"}

        patch_resource(
            resource_id="resource-123",
            url="http://new-url.com",
            repository=mock_repo,
        )

        mock_repo.resource_patch.assert_called_once_with(
            id="resource-123",
            url="http://new-url.com",
        )

    def test_patch_resource_only_description(self):
        """Test patching only the description field."""
        mock_repo = MagicMock()
        mock_repo.resource_patch.return_value = {"id": "resource-123"}

        patch_resource(
            resource_id="resource-123",
            description="New description",
            repository=mock_repo,
        )

        mock_repo.resource_patch.assert_called_once_with(
            id="resource-123",
            description="New description",
        )

    def test_patch_resource_only_format(self):
        """Test patching only the format field."""
        mock_repo = MagicMock()
        mock_repo.resource_patch.return_value = {"id": "resource-123"}

        patch_resource(
            resource_id="resource-123",
            format="PARQUET",
            repository=mock_repo,
        )

        mock_repo.resource_patch.assert_called_once_with(
            id="resource-123",
            format="PARQUET",
        )

    def test_patch_resource_not_found(self):
        """Test resource not found error during patch."""
        mock_repo = MagicMock()
        mock_repo.resource_patch.side_effect = Exception("Resource not found")

        with pytest.raises(Exception) as exc_info:
            patch_resource(
                resource_id="nonexistent-id",
                name="new-name",
                repository=mock_repo,
            )

        assert "not found" in str(exc_info.value).lower()

    def test_patch_resource_generic_error(self):
        """Test generic error handling during patch."""
        mock_repo = MagicMock()
        mock_repo.resource_patch.side_effect = Exception("Database error")

        with pytest.raises(Exception) as exc_info:
            patch_resource(
                resource_id="resource-123",
                name="new-name",
                repository=mock_repo,
            )

        assert "Error patching resource" in str(exc_info.value)

    @patch("api.services.dataset_services.patch_resource.catalog_settings")
    def test_patch_resource_uses_default_catalog(self, mock_catalog_settings):
        """Test that default catalog is used when no repository provided."""
        mock_repo = MagicMock()
        mock_repo.resource_patch.return_value = {"id": "resource-123"}
        mock_catalog_settings.local_catalog = mock_repo

        result = patch_resource(resource_id="resource-123", name="test")

        assert result["id"] == "resource-123"
        mock_repo.resource_patch.assert_called_once()


class TestDeleteResource:
    """Tests for delete_resource service."""

    def test_delete_resource_success(self):
        """Test successful resource deletion."""
        mock_repo = MagicMock()
        mock_repo.resource_delete.return_value = None

        # Should not raise
        delete_resource("resource-123", repository=mock_repo)

        mock_repo.resource_delete.assert_called_once_with(id="resource-123")

    def test_delete_resource_not_found(self):
        """Test resource not found error during deletion."""
        mock_repo = MagicMock()
        mock_repo.resource_delete.side_effect = Exception("Resource not found")

        with pytest.raises(Exception) as exc_info:
            delete_resource("nonexistent-id", repository=mock_repo)

        assert "not found" in str(exc_info.value).lower()

    def test_delete_resource_generic_error(self):
        """Test generic error handling during deletion."""
        mock_repo = MagicMock()
        mock_repo.resource_delete.side_effect = Exception("Permission denied")

        with pytest.raises(Exception) as exc_info:
            delete_resource("resource-123", repository=mock_repo)

        assert "Error deleting resource" in str(exc_info.value)

    @patch("api.services.dataset_services.delete_resource.catalog_settings")
    def test_delete_resource_uses_default_catalog(self, mock_catalog_settings):
        """Test that default catalog is used when no repository provided."""
        mock_repo = MagicMock()
        mock_repo.resource_delete.return_value = None
        mock_catalog_settings.local_catalog = mock_repo

        delete_resource("resource-123")

        mock_repo.resource_delete.assert_called_once_with(id="resource-123")
