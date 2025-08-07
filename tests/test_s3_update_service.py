# tests/test_s3_update_service.py
from unittest.mock import MagicMock, patch

import pytest

from api.services.s3_services.update_s3 import patch_s3, update_s3


class TestUpdateS3:
    """Test cases for update_s3 function."""

    @patch("api.services.s3_services.update_s3.ckan_settings")
    @pytest.mark.asyncio
    async def test_update_s3_success_all_params(self, mock_ckan_settings):
        """Test successful S3 resource update with all parameters."""
        # Mock CKAN instance and resource data
        mock_ckan = MagicMock()
        mock_ckan_settings.ckan = mock_ckan
        
        existing_resource = {
            "id": "s3-resource-123",
            "name": "old_s3_resource",
            "title": "Old S3 Resource",
            "owner_org": "test_org",
            "notes": "Old description",
            "extras": [
                {"key": "bucket", "value": "old-bucket"},
                {"key": "existing_extra", "value": "existing_value"}
            ],
            "resources": [
                {
                    "id": "resource-456",
                    "format": "s3",
                    "url": "s3://old-bucket/old-file.csv",
                    "name": "Old S3 File"
                }
            ]
        }
        
        updated_resource = existing_resource.copy()
        updated_resource["id"] = "s3-resource-123"
        
        mock_ckan.action.package_show.return_value = existing_resource
        mock_ckan.action.package_update.return_value = updated_resource
        mock_ckan.action.resource_update.return_value = {"success": True}

        result = await update_s3(
            resource_id="s3-resource-123",
            resource_name="new_s3_resource",
            resource_title="New S3 Resource",
            owner_org="new_org",
            resource_s3="s3://new-bucket/new-file.csv",
            notes="New description",
            extras={"bucket": "new-bucket", "custom_field": "custom_value"}
        )

        assert result == "s3-resource-123"
        mock_ckan.action.package_show.assert_called_once_with(id="s3-resource-123")
        mock_ckan.action.package_update.assert_called_once()
        mock_ckan.action.resource_update.assert_called_once_with(
            id="resource-456",
            url="s3://new-bucket/new-file.csv",
            package_id="s3-resource-123"
        )

        # Verify the update call contains expected data
        update_call_args = mock_ckan.action.package_update.call_args[1]
        assert update_call_args["name"] == "new_s3_resource"
        assert update_call_args["title"] == "New S3 Resource"
        assert update_call_args["owner_org"] == "new_org"
        assert update_call_args["notes"] == "New description"

        # Verify extras contain all expected values
        extras_dict = {extra["key"]: extra["value"] for extra in update_call_args["extras"]}
        assert extras_dict["bucket"] == "new-bucket"
        assert extras_dict["custom_field"] == "custom_value"
        assert extras_dict["existing_extra"] == "existing_value"  # Preserved

    @patch("api.services.s3_services.update_s3.ckan_settings")
    @pytest.mark.asyncio
    async def test_update_s3_with_custom_ckan_instance(self, mock_ckan_settings):
        """Test update_s3 with custom CKAN instance."""
        custom_ckan = MagicMock()
        existing_resource = {
            "id": "s3-resource-123",
            "name": "test_s3",
            "title": "Test S3",
            "owner_org": "test_org",
            "extras": [],
            "resources": []
        }
        
        custom_ckan.action.package_show.return_value = existing_resource
        custom_ckan.action.package_update.return_value = existing_resource

        result = await update_s3(
            resource_id="s3-resource-123",
            resource_name="updated_s3",
            ckan_instance=custom_ckan
        )

        assert result == "s3-resource-123"
        custom_ckan.action.package_show.assert_called_once_with(id="s3-resource-123")
        # Should not use default ckan_settings.ckan
        mock_ckan_settings.ckan.action.package_show.assert_not_called()

    @patch("api.services.s3_services.update_s3.ckan_settings")
    @pytest.mark.asyncio
    async def test_update_s3_reserved_keys_error(self, mock_ckan_settings):
        """Test update_s3 with reserved keys in extras."""
        mock_ckan = MagicMock()
        mock_ckan_settings.ckan = mock_ckan
        
        existing_resource = {
            "id": "s3-resource-123",
            "name": "test_s3",
            "title": "Test S3",
            "owner_org": "test_org",
            "extras": []
        }
        
        mock_ckan.action.package_show.return_value = existing_resource

        with pytest.raises(KeyError, match="Extras contain reserved keys"):
            await update_s3(
                resource_id="s3-resource-123",
                extras={"name": "invalid", "id": "invalid", "custom": "valid"}
            )

    @patch("api.services.s3_services.update_s3.ckan_settings")
    @pytest.mark.asyncio
    async def test_update_s3_fetch_error(self, mock_ckan_settings):
        """Test update_s3 when fetching resource fails."""
        mock_ckan = MagicMock()
        mock_ckan_settings.ckan = mock_ckan
        mock_ckan.action.package_show.side_effect = Exception("Resource not found")

        with pytest.raises(Exception, match="Error fetching S3 resource: Resource not found"):
            await update_s3(resource_id="nonexistent-resource")

    @patch("api.services.s3_services.update_s3.ckan_settings")
    @pytest.mark.asyncio
    async def test_update_s3_update_error(self, mock_ckan_settings):
        """Test update_s3 when updating resource fails."""
        mock_ckan = MagicMock()
        mock_ckan_settings.ckan = mock_ckan
        
        existing_resource = {
            "id": "s3-resource-123",
            "name": "test_s3",
            "title": "Test S3",
            "owner_org": "test_org",
            "extras": [],
            "resources": []
        }
        
        mock_ckan.action.package_show.return_value = existing_resource
        mock_ckan.action.package_update.side_effect = Exception("Update failed")

        with pytest.raises(Exception, match="Error updating S3 resource: Update failed"):
            await update_s3(resource_id="s3-resource-123", resource_name="new_name")

    @patch("api.services.s3_services.update_s3.ckan_settings")
    @pytest.mark.asyncio
    async def test_update_s3_no_extras_provided(self, mock_ckan_settings):
        """Test update_s3 without extras."""
        mock_ckan = MagicMock()
        mock_ckan_settings.ckan = mock_ckan
        
        existing_resource = {
            "id": "s3-resource-123",
            "name": "test_s3",
            "title": "Test S3",
            "owner_org": "test_org",
            "extras": [{"key": "existing", "value": "preserved"}],
            "resources": []
        }
        
        mock_ckan.action.package_show.return_value = existing_resource
        mock_ckan.action.package_update.return_value = existing_resource

        result = await update_s3(
            resource_id="s3-resource-123",
            resource_name="updated_s3"
        )

        assert result == "s3-resource-123"
        
        # Verify existing extras are preserved
        update_call_args = mock_ckan.action.package_update.call_args[1]
        extras_dict = {extra["key"]: extra["value"] for extra in update_call_args["extras"]}
        assert extras_dict["existing"] == "preserved"

    @patch("api.services.s3_services.update_s3.ckan_settings")
    @pytest.mark.asyncio
    async def test_update_s3_without_s3_resource_update(self, mock_ckan_settings):
        """Test update_s3 without S3 URL update."""
        mock_ckan = MagicMock()
        mock_ckan_settings.ckan = mock_ckan
        
        existing_resource = {
            "id": "s3-resource-123",
            "name": "test_s3",
            "title": "Test S3",
            "owner_org": "test_org",
            "extras": [],
            "resources": [
                {"id": "resource-456", "format": "s3", "url": "s3://old-bucket/file.csv"}
            ]
        }
        
        mock_ckan.action.package_show.return_value = existing_resource
        mock_ckan.action.package_update.return_value = existing_resource

        result = await update_s3(
            resource_id="s3-resource-123",
            resource_name="updated_s3"
            # No resource_s3 parameter
        )

        assert result == "s3-resource-123"
        mock_ckan.action.package_update.assert_called_once()
        # resource_update should not be called
        mock_ckan.action.resource_update.assert_not_called()

    @patch("api.services.s3_services.update_s3.ckan_settings")
    @pytest.mark.asyncio
    async def test_update_s3_case_insensitive_format(self, mock_ckan_settings):
        """Test update_s3 with case-insensitive S3 format matching."""
        mock_ckan = MagicMock()
        mock_ckan_settings.ckan = mock_ckan
        
        existing_resource = {
            "id": "s3-resource-123",
            "name": "test_s3",
            "title": "Test S3",
            "owner_org": "test_org",
            "extras": [],
            "resources": [
                {"id": "resource-456", "format": "S3", "url": "s3://old-bucket/file.csv"}
            ]
        }
        
        mock_ckan.action.package_show.return_value = existing_resource
        mock_ckan.action.package_update.return_value = existing_resource
        mock_ckan.action.resource_update.return_value = {"success": True}

        result = await update_s3(
            resource_id="s3-resource-123",
            resource_s3="s3://new-bucket/new-file.csv"
        )

        assert result == "s3-resource-123"
        mock_ckan.action.resource_update.assert_called_once_with(
            id="resource-456",
            url="s3://new-bucket/new-file.csv",
            package_id="s3-resource-123"
        )


class TestPatchS3:
    """Test cases for patch_s3 function."""

    @patch("api.services.s3_services.update_s3.ckan_settings")
    @pytest.mark.asyncio
    async def test_patch_s3_success(self, mock_ckan_settings):
        """Test successful S3 resource patch with partial updates."""
        mock_ckan = MagicMock()
        mock_ckan_settings.ckan = mock_ckan
        
        existing_resource = {
            "id": "s3-resource-123",
            "name": "existing_s3",
            "title": "Existing S3 Resource",
            "owner_org": "test_org",
            "notes": "Existing description",
            "extras": [
                {"key": "bucket", "value": "existing-bucket"},
                {"key": "existing_extra", "value": "existing_value"}
            ],
            "resources": []
        }
        
        mock_ckan.action.package_show.return_value = existing_resource
        mock_ckan.action.package_update.return_value = existing_resource

        result = await patch_s3(
            resource_id="s3-resource-123",
            resource_title="Updated S3 Resource",
            extras={"bucket": "new-bucket", "new_field": "new_value"}
        )

        assert result == "s3-resource-123"
        mock_ckan.action.package_show.assert_called_once_with(id="s3-resource-123")
        
        # Verify only specified fields were updated
        update_call_args = mock_ckan.action.package_update.call_args[1]
        assert update_call_args["name"] == "existing_s3"  # Unchanged
        assert update_call_args["title"] == "Updated S3 Resource"  # Changed
        assert update_call_args["notes"] == "Existing description"  # Unchanged
        
        # Verify extras were merged correctly
        extras_dict = {extra["key"]: extra["value"] for extra in update_call_args["extras"]}
        assert extras_dict["bucket"] == "new-bucket"  # Updated
        assert extras_dict["existing_extra"] == "existing_value"  # Preserved
        assert extras_dict["new_field"] == "new_value"  # Added

    @patch("api.services.s3_services.update_s3.ckan_settings")
    @pytest.mark.asyncio
    async def test_patch_s3_reserved_keys_error(self, mock_ckan_settings):
        """Test patch_s3 with reserved keys in extras."""
        mock_ckan = MagicMock()
        mock_ckan_settings.ckan = mock_ckan
        
        existing_resource = {
            "id": "s3-resource-123",
            "name": "test_s3",
            "title": "Test S3",
            "owner_org": "test_org",
            "extras": []
        }
        
        mock_ckan.action.package_show.return_value = existing_resource

        with pytest.raises(KeyError, match="Extras contain reserved keys"):
            await patch_s3(
                resource_id="s3-resource-123",
                extras={"title": "invalid", "owner_org": "also_invalid"}
            )

    @patch("api.services.s3_services.update_s3.ckan_settings")
    @pytest.mark.asyncio
    async def test_patch_s3_fetch_error(self, mock_ckan_settings):
        """Test patch_s3 when fetching resource fails."""
        mock_ckan = MagicMock()
        mock_ckan_settings.ckan = mock_ckan
        mock_ckan.action.package_show.side_effect = Exception("Resource not found")

        with pytest.raises(Exception, match="Error fetching S3 resource: Resource not found"):
            await patch_s3(resource_id="nonexistent-resource", resource_title="New Title")

    @patch("api.services.s3_services.update_s3.ckan_settings")
    @pytest.mark.asyncio
    async def test_patch_s3_update_error(self, mock_ckan_settings):
        """Test patch_s3 when updating resource fails."""
        mock_ckan = MagicMock()
        mock_ckan_settings.ckan = mock_ckan
        
        existing_resource = {
            "id": "s3-resource-123",
            "name": "test_s3",
            "title": "Test S3",
            "owner_org": "test_org",
            "extras": [],
            "resources": []
        }
        
        mock_ckan.action.package_show.return_value = existing_resource
        mock_ckan.action.package_update.side_effect = Exception("Update failed")

        with pytest.raises(Exception, match="Error updating S3 resource: Update failed"):
            await patch_s3(resource_id="s3-resource-123", resource_title="New Title")

    @patch("api.services.s3_services.update_s3.ckan_settings")
    @pytest.mark.asyncio
    async def test_patch_s3_with_s3_url_update(self, mock_ckan_settings):
        """Test patch_s3 updates S3 URL in resources."""
        mock_ckan = MagicMock()
        mock_ckan_settings.ckan = mock_ckan
        
        existing_resource = {
            "id": "s3-resource-123",
            "name": "test_s3",
            "title": "Test S3",
            "owner_org": "test_org",
            "extras": [],
            "resources": [
                {"id": "resource-456", "format": "s3", "url": "s3://old-bucket/old-file.csv"}
            ]
        }
        
        mock_ckan.action.package_show.return_value = existing_resource
        mock_ckan.action.package_update.return_value = existing_resource
        mock_ckan.action.resource_update.return_value = {"success": True}

        result = await patch_s3(
            resource_id="s3-resource-123",
            resource_s3="s3://patched-bucket/patched-file.csv"
        )

        assert result == "s3-resource-123"
        
        # Verify S3 resource URL was updated
        mock_ckan.action.resource_update.assert_called_once_with(
            id="resource-456",
            url="s3://patched-bucket/patched-file.csv",
            package_id="s3-resource-123"
        )

    @patch("api.services.s3_services.update_s3.ckan_settings")
    @pytest.mark.asyncio
    async def test_patch_s3_no_extras_provided(self, mock_ckan_settings):
        """Test patch_s3 without extras."""
        mock_ckan = MagicMock()
        mock_ckan_settings.ckan = mock_ckan
        
        existing_resource = {
            "id": "s3-resource-123",
            "name": "test_s3",
            "title": "Test S3",
            "owner_org": "test_org",
            "extras": [{"key": "existing", "value": "value"}],
            "resources": []
        }
        
        mock_ckan.action.package_show.return_value = existing_resource
        mock_ckan.action.package_update.return_value = existing_resource

        result = await patch_s3(
            resource_id="s3-resource-123",
            resource_name="patched_s3"
        )

        assert result == "s3-resource-123"
        
        # Verify existing extras are not modified when no extras provided
        update_call_args = mock_ckan.action.package_update.call_args[1]
        # When no extras are provided, the extras key should not be in the update call
        # or should preserve existing ones without modification
        assert update_call_args["name"] == "patched_s3"

    @patch("api.services.s3_services.update_s3.ckan_settings")
    @pytest.mark.asyncio
    async def test_patch_s3_individual_fields(self, mock_ckan_settings):
        """Test patch_s3 updating individual fields separately."""
        mock_ckan = MagicMock()
        mock_ckan_settings.ckan = mock_ckan
        
        existing_resource = {
            "id": "s3-resource-123",
            "name": "test_s3",
            "title": "Test S3",
            "owner_org": "test_org",
            "notes": "old notes",
            "extras": [],
            "resources": []
        }
        
        mock_ckan.action.package_show.return_value = existing_resource
        mock_ckan.action.package_update.return_value = existing_resource

        result = await patch_s3(
            resource_id="s3-resource-123",
            resource_name="patched_s3",
            owner_org="new_org",
            notes="patched description"
        )

        assert result == "s3-resource-123"
        
        # Verify individual field updates
        update_call_args = mock_ckan.action.package_update.call_args[1]
        assert update_call_args["name"] == "patched_s3"  # Updated
        assert update_call_args["title"] == "Test S3"  # Unchanged
        assert update_call_args["owner_org"] == "new_org"  # Updated
        assert update_call_args["notes"] == "patched description"  # Updated
