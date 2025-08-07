# tests/test_update_service.py
from unittest.mock import MagicMock, patch

import pytest

from api.services.service_services.update_service import patch_service, update_service


class TestUpdateService:
    """Test cases for update_service function."""

    @patch("api.services.service_services.update_service.ckan_settings")
    def test_update_service_success_all_params(self, mock_ckan_settings):
        """Test successful service update with all parameters."""
        # Mock CKAN instance and service data
        mock_ckan = MagicMock()
        mock_ckan_settings.ckan = mock_ckan
        
        existing_service = {
            "id": "service-123",
            "name": "old_service",
            "title": "Old Service",
            "owner_org": "services",
            "notes": "Old notes",
            "extras": [
                {"key": "service_type", "value": "API"},
                {"key": "existing_extra", "value": "existing_value"}
            ],
            "resources": [
                {"format": "service", "url": "http://old-url.com", "description": "Old description"}
            ]
        }
        
        updated_service = existing_service.copy()
        updated_service["id"] = "service-123"
        
        mock_ckan.action.package_show.return_value = existing_service
        mock_ckan.action.package_update.return_value = updated_service

        result = update_service(
            service_id="service-123",
            service_name="new_service",
            service_title="New Service",
            owner_org="services",
            service_url="http://new-url.com",
            service_type="Web Service",
            notes="New notes",
            extras={"custom_field": "custom_value"},
            health_check_url="http://health.com",
            documentation_url="http://docs.com"
        )

        assert result == "service-123"
        mock_ckan.action.package_show.assert_called_once_with(id="service-123")
        mock_ckan.action.package_update.assert_called_once()

    @patch("api.services.service_services.update_service.ckan_settings")
    def test_update_service_with_custom_ckan_instance(self, mock_ckan_settings):
        """Test update_service with custom CKAN instance."""
        custom_ckan = MagicMock()
        existing_service = {
            "id": "service-123",
            "name": "test_service",
            "title": "Test Service",
            "owner_org": "services",
            "extras": [],
            "resources": []
        }
        
        custom_ckan.action.package_show.return_value = existing_service
        custom_ckan.action.package_update.return_value = existing_service

        result = update_service(
            service_id="service-123",
            service_name="updated_service",
            ckan_instance=custom_ckan
        )

        assert result == "service-123"
        custom_ckan.action.package_show.assert_called_once_with(id="service-123")
        # Should not use default ckan_settings.ckan
        mock_ckan_settings.ckan.action.package_show.assert_not_called()

    @patch("api.services.service_services.update_service.ckan_settings")
    def test_update_service_invalid_owner_org(self, mock_ckan_settings):
        """Test update_service with invalid owner_org."""
        with pytest.raises(ValueError, match="owner_org must be 'services'"):
            update_service(
                service_id="service-123",
                owner_org="invalid_org"
            )

    @patch("api.services.service_services.update_service.ckan_settings")
    def test_update_service_invalid_extras_type(self, mock_ckan_settings):
        """Test update_service with invalid extras type."""
        with pytest.raises(ValueError, match="Extras must be a dictionary or None"):
            update_service(
                service_id="service-123",
                extras="invalid_extras"
            )

    @patch("api.services.service_services.update_service.ckan_settings")
    def test_update_service_reserved_keys_in_extras(self, mock_ckan_settings):
        """Test update_service with reserved keys in extras."""
        with pytest.raises(KeyError, match="Extras contain reserved keys"):
            update_service(
                service_id="service-123",
                extras={"name": "invalid", "custom_field": "valid"}
            )

    @patch("api.services.service_services.update_service.ckan_settings")
    def test_update_service_fetch_error(self, mock_ckan_settings):
        """Test update_service when fetching service fails."""
        mock_ckan = MagicMock()
        mock_ckan_settings.ckan = mock_ckan
        mock_ckan.action.package_show.side_effect = Exception("Service not found")

        with pytest.raises(Exception, match="Error fetching service: Service not found"):
            update_service(service_id="nonexistent-service")

    @patch("api.services.service_services.update_service.ckan_settings")
    def test_update_service_update_error(self, mock_ckan_settings):
        """Test update_service when updating service fails."""
        mock_ckan = MagicMock()
        mock_ckan_settings.ckan = mock_ckan
        
        existing_service = {
            "id": "service-123",
            "name": "test_service",
            "title": "Test Service",
            "owner_org": "services",
            "extras": [],
            "resources": []
        }
        
        mock_ckan.action.package_show.return_value = existing_service
        mock_ckan.action.package_update.side_effect = Exception("Update failed")

        with pytest.raises(Exception, match="Error updating service: Update failed"):
            update_service(service_id="service-123", service_name="new_name")

    @patch("api.services.service_services.update_service.ckan_settings")
    def test_update_service_no_extras_provided(self, mock_ckan_settings):
        """Test update_service with service-specific fields but no user extras."""
        mock_ckan = MagicMock()
        mock_ckan_settings.ckan = mock_ckan
        
        existing_service = {
            "id": "service-123",
            "name": "test_service",
            "title": "Test Service",
            "owner_org": "services",
            "extras": [{"key": "existing_key", "value": "existing_value"}],
            "resources": []
        }
        
        mock_ckan.action.package_show.return_value = existing_service
        mock_ckan.action.package_update.return_value = existing_service

        result = update_service(
            service_id="service-123",
            service_type="API",
            health_check_url="http://health.com"
        )

        assert result == "service-123"
        
        # Verify service was updated with service-specific extras
        update_call_args = mock_ckan.action.package_update.call_args[1]
        extras_dict = {extra["key"]: extra["value"] for extra in update_call_args["extras"]}
        assert extras_dict["service_type"] == "API"
        assert extras_dict["health_check_url"] == "http://health.com"
        assert extras_dict["existing_key"] == "existing_value"

    @patch("api.services.service_services.update_service.ckan_settings")
    def test_update_service_update_resource_url(self, mock_ckan_settings):
        """Test update_service updates service URL in resources."""
        mock_ckan = MagicMock()
        mock_ckan_settings.ckan = mock_ckan
        
        existing_service = {
            "id": "service-123",
            "name": "test_service",
            "title": "Test Service",
            "owner_org": "services",
            "extras": [],
            "resources": [
                {"format": "service", "url": "http://old-url.com", "description": "Old description"},
                {"format": "other", "url": "http://other.com", "description": "Other resource"}
            ]
        }
        
        mock_ckan.action.package_show.return_value = existing_service
        mock_ckan.action.package_update.return_value = existing_service

        result = update_service(
            service_id="service-123",
            service_url="http://new-service-url.com",
            service_name="updated_service"
        )

        assert result == "service-123"
        
        # Verify service resource URL was updated
        update_call_args = mock_ckan.action.package_update.call_args[1]
        service_resource = next(
            res for res in update_call_args["resources"] 
            if res["format"] == "service"
        )
        assert service_resource["url"] == "http://new-service-url.com"
        assert "Test Service" in service_resource["description"]  # Uses existing title, not service_name


class TestPatchService:
    """Test cases for patch_service function."""

    @patch("api.services.service_services.update_service.ckan_settings")
    def test_patch_service_success(self, mock_ckan_settings):
        """Test successful service patch with partial updates."""
        mock_ckan = MagicMock()
        mock_ckan_settings.ckan = mock_ckan
        
        existing_service = {
            "id": "service-123",
            "name": "existing_service",
            "title": "Existing Service",
            "owner_org": "services",
            "notes": "Existing notes",
            "extras": [
                {"key": "service_type", "value": "API"},
                {"key": "existing_extra", "value": "existing_value"}
            ],
            "resources": []
        }
        
        mock_ckan.action.package_show.return_value = existing_service
        mock_ckan.action.package_update.return_value = existing_service

        result = patch_service(
            service_id="service-123",
            service_title="Updated Service Title",
            service_type="Web Service",
            extras={"new_field": "new_value"}
        )

        assert result == "service-123"
        mock_ckan.action.package_show.assert_called_once_with(id="service-123")
        
        # Verify only specified fields were updated
        update_call_args = mock_ckan.action.package_update.call_args[1]
        assert update_call_args["name"] == "existing_service"  # Unchanged
        assert update_call_args["title"] == "Updated Service Title"  # Changed
        assert update_call_args["notes"] == "Existing notes"  # Unchanged
        
        # Verify extras were merged correctly
        extras_dict = {extra["key"]: extra["value"] for extra in update_call_args["extras"]}
        assert extras_dict["service_type"] == "Web Service"  # Updated
        assert extras_dict["existing_extra"] == "existing_value"  # Preserved
        assert extras_dict["new_field"] == "new_value"  # Added

    @patch("api.services.service_services.update_service.ckan_settings")
    def test_patch_service_invalid_owner_org(self, mock_ckan_settings):
        """Test patch_service with invalid owner_org."""
        with pytest.raises(ValueError, match="owner_org must be 'services'"):
            patch_service(
                service_id="service-123",
                owner_org="invalid_org"
            )

    @patch("api.services.service_services.update_service.ckan_settings")
    def test_patch_service_invalid_extras_type(self, mock_ckan_settings):
        """Test patch_service with invalid extras type."""
        with pytest.raises(ValueError, match="Extras must be a dictionary or None"):
            patch_service(
                service_id="service-123",
                extras=["invalid", "extras"]
            )

    @patch("api.services.service_services.update_service.ckan_settings")
    def test_patch_service_reserved_keys_in_extras(self, mock_ckan_settings):
        """Test patch_service with reserved keys in extras."""
        with pytest.raises(KeyError, match="Extras contain reserved keys"):
            patch_service(
                service_id="service-123",
                extras={"id": "invalid", "title": "also_invalid"}
            )

    @patch("api.services.service_services.update_service.ckan_settings")
    def test_patch_service_fetch_error(self, mock_ckan_settings):
        """Test patch_service when fetching service fails."""
        mock_ckan = MagicMock()
        mock_ckan_settings.ckan = mock_ckan
        mock_ckan.action.package_show.side_effect = Exception("Service not found")

        with pytest.raises(Exception, match="Error fetching service: Service not found"):
            patch_service(service_id="nonexistent-service", service_title="New Title")

    @patch("api.services.service_services.update_service.ckan_settings")
    def test_patch_service_update_error(self, mock_ckan_settings):
        """Test patch_service when updating service fails."""
        mock_ckan = MagicMock()
        mock_ckan_settings.ckan = mock_ckan
        
        existing_service = {
            "id": "service-123",
            "name": "test_service",
            "title": "Test Service",
            "owner_org": "services",
            "extras": [],
            "resources": []
        }
        
        mock_ckan.action.package_show.return_value = existing_service
        mock_ckan.action.package_update.side_effect = Exception("Update failed")

        with pytest.raises(Exception, match="Error updating service: Update failed"):
            patch_service(service_id="service-123", service_title="New Title")

    @patch("api.services.service_services.update_service.ckan_settings")
    def test_patch_service_with_service_url_update(self, mock_ckan_settings):
        """Test patch_service updates service URL in resources."""
        mock_ckan = MagicMock()
        mock_ckan_settings.ckan = mock_ckan
        
        existing_service = {
            "id": "service-123",
            "name": "test_service",
            "title": "Test Service",
            "owner_org": "services",
            "extras": [],
            "resources": [
                {"format": "service", "url": "http://old-url.com", "description": "Old description"}
            ]
        }
        
        mock_ckan.action.package_show.return_value = existing_service
        mock_ckan.action.package_update.return_value = existing_service

        result = patch_service(
            service_id="service-123",
            service_url="http://patched-url.com"
        )

        assert result == "service-123"
        
        # Verify service resource URL was updated
        update_call_args = mock_ckan.action.package_update.call_args[1]
        service_resource = update_call_args["resources"][0]
        assert service_resource["url"] == "http://patched-url.com"
        assert "http://patched-url.com" in service_resource["description"]

    @patch("api.services.service_services.update_service.ckan_settings")
    def test_patch_service_no_changes(self, mock_ckan_settings):
        """Test patch_service with no actual changes (all None parameters)."""
        mock_ckan = MagicMock()
        mock_ckan_settings.ckan = mock_ckan
        
        existing_service = {
            "id": "service-123",
            "name": "test_service",
            "title": "Test Service",
            "owner_org": "services",
            "extras": [{"key": "existing", "value": "value"}],
            "resources": []
        }
        
        mock_ckan.action.package_show.return_value = existing_service
        mock_ckan.action.package_update.return_value = existing_service

        result = patch_service(service_id="service-123")

        assert result == "service-123"
        
        # Verify service structure is preserved
        update_call_args = mock_ckan.action.package_update.call_args[1]
        assert update_call_args["name"] == "test_service"
        assert update_call_args["title"] == "Test Service"
        assert len(update_call_args["extras"]) == 1
        assert update_call_args["extras"][0]["key"] == "existing"
