# tests/test_update_dataset_service.py
"""Tests for update_dataset service."""

import pytest
from unittest.mock import MagicMock, patch

from api.services.url_services.update_dataset import update_dataset


class TestUpdateDataset:
    """Tests for update_dataset service."""

    @pytest.mark.asyncio
    @patch("api.services.url_services.update_dataset.ckan_settings")
    async def test_update_dataset_success(self, mock_ckan_settings):
        """Test successful dataset update."""
        mock_ckan = MagicMock()
        mock_ckan.action.package_show.return_value = {
            "id": "dataset-123",
            "title": "Original Title",
            "notes": "Original notes",
            "tags": [{"name": "tag1"}],
            "groups": [{"name": "group1"}],
            "extras": [{"key": "key1", "value": "value1"}],
        }
        mock_ckan_settings.ckan = mock_ckan

        data = MagicMock()
        data.title = "New Title"
        data.notes = "New notes"
        data.tags = ["tag2"]
        data.groups = ["group2"]
        data.extras = {"key2": "value2"}
        data.resources = None

        result = await update_dataset("dataset-123", data)

        assert result["message"] == "Dataset updated successfully with additional resources."
        mock_ckan.action.package_patch.assert_called_once()

    @pytest.mark.asyncio
    @patch("api.services.url_services.update_dataset.ckan_settings")
    async def test_update_dataset_with_resources(self, mock_ckan_settings):
        """Test dataset update with new resources."""
        mock_ckan = MagicMock()
        mock_ckan.action.package_show.return_value = {
            "id": "dataset-123",
            "title": "Title",
            "notes": "Notes",
            "tags": [],
            "groups": [],
            "extras": [],
        }
        mock_ckan_settings.ckan = mock_ckan

        mock_resource = MagicMock()
        mock_resource.resource_url = "http://example.com/data.csv"
        mock_resource.format = "CSV"
        mock_resource.name = "Data File"
        mock_resource.description = "Test data file"

        data = MagicMock()
        data.title = None
        data.notes = None
        data.tags = None
        data.groups = None
        data.extras = None
        data.resources = [mock_resource]

        result = await update_dataset("dataset-123", data)

        assert result["message"] == "Dataset updated successfully with additional resources."
        mock_ckan.action.resource_create.assert_called_once_with(
            package_id="dataset-123",
            url="http://example.com/data.csv",
            format="CSV",
            name="Data File",
            description="Test data file",
        )

    @pytest.mark.asyncio
    @patch("api.services.url_services.update_dataset.ckan_settings")
    async def test_update_dataset_fetch_error(self, mock_ckan_settings):
        """Test error when fetching dataset fails."""
        mock_ckan = MagicMock()
        mock_ckan.action.package_show.side_effect = Exception("Not found")
        mock_ckan_settings.ckan = mock_ckan

        data = MagicMock()

        with pytest.raises(Exception) as exc_info:
            await update_dataset("nonexistent", data)

        assert "Cannot fetch dataset" in str(exc_info.value)

    @pytest.mark.asyncio
    @patch("api.services.url_services.update_dataset.ckan_settings")
    async def test_update_dataset_patch_error(self, mock_ckan_settings):
        """Test error when patching dataset fails."""
        mock_ckan = MagicMock()
        mock_ckan.action.package_show.return_value = {
            "id": "dataset-123",
            "title": "Title",
            "notes": "Notes",
            "tags": [],
            "groups": [],
            "extras": [],
        }
        mock_ckan.action.package_patch.side_effect = Exception("Patch failed")
        mock_ckan_settings.ckan = mock_ckan

        data = MagicMock()
        data.title = None
        data.notes = None
        data.tags = None
        data.groups = None
        data.extras = None
        data.resources = None

        with pytest.raises(Exception) as exc_info:
            await update_dataset("dataset-123", data)

        assert "Failed to patch dataset" in str(exc_info.value)

    @pytest.mark.asyncio
    @patch("api.services.url_services.update_dataset.ckan_settings")
    async def test_update_dataset_resource_create_error(self, mock_ckan_settings):
        """Test error when creating resource fails."""
        mock_ckan = MagicMock()
        mock_ckan.action.package_show.return_value = {
            "id": "dataset-123",
            "title": "Title",
            "notes": "Notes",
            "tags": [],
            "groups": [],
            "extras": [],
        }
        mock_ckan.action.resource_create.side_effect = Exception("Resource error")
        mock_ckan_settings.ckan = mock_ckan

        mock_resource = MagicMock()
        mock_resource.resource_url = "http://example.com/data.csv"
        mock_resource.format = "CSV"
        mock_resource.name = "Data File"
        mock_resource.description = "Test data file"

        data = MagicMock()
        data.title = None
        data.notes = None
        data.tags = None
        data.groups = None
        data.extras = None
        data.resources = [mock_resource]

        with pytest.raises(Exception) as exc_info:
            await update_dataset("dataset-123", data)

        assert "Failed to add resource" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_update_dataset_with_custom_ckan_instance(self):
        """Test update with custom CKAN instance."""
        mock_ckan = MagicMock()
        mock_ckan.action.package_show.return_value = {
            "id": "dataset-123",
            "title": "Title",
            "notes": "Notes",
            "tags": [],
            "groups": [],
            "extras": [],
        }

        data = MagicMock()
        data.title = "Updated"
        data.notes = None
        data.tags = None
        data.groups = None
        data.extras = None
        data.resources = None

        result = await update_dataset("dataset-123", data, ckan_instance=mock_ckan)

        assert "successfully" in result["message"]

    @pytest.mark.asyncio
    @patch("api.services.url_services.update_dataset.ckan_settings")
    async def test_update_dataset_merge_tags(self, mock_ckan_settings):
        """Test that tags are merged (not replaced)."""
        mock_ckan = MagicMock()
        mock_ckan.action.package_show.return_value = {
            "id": "dataset-123",
            "title": "Title",
            "notes": "Notes",
            "tags": [{"name": "existing-tag"}],
            "groups": [],
            "extras": [],
        }
        mock_ckan_settings.ckan = mock_ckan

        data = MagicMock()
        data.title = None
        data.notes = None
        data.tags = ["new-tag"]
        data.groups = None
        data.extras = None
        data.resources = None

        await update_dataset("dataset-123", data)

        call_args = mock_ckan.action.package_patch.call_args
        tags = call_args[1]["tags"]
        tag_names = {t["name"] for t in tags}
        assert "existing-tag" in tag_names
        assert "new-tag" in tag_names

    @pytest.mark.asyncio
    @patch("api.services.url_services.update_dataset.ckan_settings")
    async def test_update_dataset_merge_extras(self, mock_ckan_settings):
        """Test that extras are merged (not replaced)."""
        mock_ckan = MagicMock()
        mock_ckan.action.package_show.return_value = {
            "id": "dataset-123",
            "title": "Title",
            "notes": "Notes",
            "tags": [],
            "groups": [],
            "extras": [{"key": "existing", "value": "old"}],
        }
        mock_ckan_settings.ckan = mock_ckan

        data = MagicMock()
        data.title = None
        data.notes = None
        data.tags = None
        data.groups = None
        data.extras = {"new": "value"}
        data.resources = None

        await update_dataset("dataset-123", data)

        call_args = mock_ckan.action.package_patch.call_args
        extras = call_args[1]["extras"]
        extras_dict = {e["key"]: e["value"] for e in extras}
        assert extras_dict["existing"] == "old"
        assert extras_dict["new"] == "value"
