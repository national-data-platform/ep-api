# tests/test_create_organization_service.py
"""
Tests for create_organization service.
"""

import pytest
from unittest.mock import MagicMock, patch
from ckanapi import NotFound, ValidationError

from api.services.organization_services.create_organization import create_organization


class TestCreateOrganization:
    """Test cases for create_organization function."""

    @patch("api.services.organization_services.create_organization.catalog_settings")
    def test_create_organization_local_server(self, mock_catalog_settings):
        """Test creating organization on local server."""
        mock_repository = MagicMock()
        mock_repository.organization_create.return_value = {
            "id": "org-123",
            "name": "test-org",
            "title": "Test Organization",
        }
        mock_catalog_settings.local_catalog = mock_repository

        result = create_organization(
            name="test-org", title="Test Organization", server="local"
        )

        assert result == "org-123"
        mock_repository.organization_create.assert_called_once_with(
            name="test-org", title="Test Organization", description=None
        )

    @patch("api.services.organization_services.create_organization.ckan_settings")
    @patch("api.services.organization_services.create_organization.catalog_settings")
    def test_create_organization_pre_ckan_server(
        self, mock_catalog_settings, mock_ckan_settings
    ):
        """Test creating organization on pre_ckan server."""
        mock_ckan_settings.pre_ckan_enabled = True

        mock_repository = MagicMock()
        mock_repository.organization_create.return_value = {
            "id": "pre-org-456",
            "name": "pre-org",
        }
        mock_catalog_settings.pre_catalog = mock_repository

        result = create_organization(
            name="pre-org", title="Pre Organization", server="pre_ckan"
        )

        assert result == "pre-org-456"
        mock_repository.organization_create.assert_called_once()

    @patch("api.services.organization_services.create_organization.ckan_settings")
    def test_create_organization_pre_ckan_disabled(self, mock_ckan_settings):
        """Test that pre_ckan raises error when disabled."""
        mock_ckan_settings.pre_ckan_enabled = False

        with pytest.raises(Exception) as exc_info:
            create_organization(name="test-org", title="Test Org", server="pre_ckan")

        assert "Pre-CKAN is disabled" in str(exc_info.value)

    @patch("api.services.organization_services.create_organization.catalog_settings")
    def test_create_organization_with_description(self, mock_catalog_settings):
        """Test creating organization with description."""
        mock_repository = MagicMock()
        mock_repository.organization_create.return_value = {
            "id": "org-789",
            "name": "described-org",
        }
        mock_catalog_settings.local_catalog = mock_repository

        result = create_organization(
            name="described-org",
            title="Described Organization",
            description="This is a test organization",
            server="local",
        )

        assert result == "org-789"
        call_args = mock_repository.organization_create.call_args[1]
        assert call_args["description"] == "This is a test organization"

    @patch("api.services.organization_services.create_organization.catalog_settings")
    def test_create_organization_validation_error(self, mock_catalog_settings):
        """Test handling of validation error."""
        mock_repository = MagicMock()
        validation_error = ValidationError({"name": ["Invalid name"]})
        mock_repository.organization_create.side_effect = validation_error
        mock_catalog_settings.local_catalog = mock_repository

        with pytest.raises(Exception) as exc_info:
            create_organization(name="invalid-org", title="Invalid Org", server="local")

        assert "Validation error" in str(exc_info.value)

    @patch("api.services.organization_services.create_organization.catalog_settings")
    def test_create_organization_not_found_error(self, mock_catalog_settings):
        """Test handling of NotFound error."""
        mock_repository = MagicMock()
        mock_repository.organization_create.side_effect = NotFound()
        mock_catalog_settings.local_catalog = mock_repository

        with pytest.raises(Exception) as exc_info:
            create_organization(name="test-org", title="Test Org", server="local")

        assert "not found" in str(exc_info.value).lower()

    @patch("api.services.organization_services.create_organization.catalog_settings")
    def test_create_organization_duplicate_name(self, mock_catalog_settings):
        """Test handling of duplicate organization name."""
        mock_repository = MagicMock()
        mock_repository.organization_create.side_effect = Exception(
            "Group name already exists in database"
        )
        mock_catalog_settings.local_catalog = mock_repository

        with pytest.raises(Exception) as exc_info:
            create_organization(
                name="duplicate-org", title="Duplicate Org", server="local"
            )

        assert "already exists" in str(exc_info.value)

    @patch("api.services.organization_services.create_organization.catalog_settings")
    def test_create_organization_generic_error(self, mock_catalog_settings):
        """Test handling of generic errors."""
        mock_repository = MagicMock()
        mock_repository.organization_create.side_effect = Exception(
            "Connection timeout"
        )
        mock_catalog_settings.local_catalog = mock_repository

        with pytest.raises(Exception) as exc_info:
            create_organization(name="test-org", title="Test Org", server="local")

        assert "Error creating organization" in str(exc_info.value)
        assert "Connection timeout" in str(exc_info.value)

    @patch("api.services.organization_services.create_organization.catalog_settings")
    def test_create_organization_default_server_is_local(self, mock_catalog_settings):
        """Test that default server is 'local'."""
        mock_repository = MagicMock()
        mock_repository.organization_create.return_value = {
            "id": "default-org",
            "name": "default",
        }
        mock_catalog_settings.local_catalog = mock_repository

        result = create_organization(name="default", title="Default Org")

        assert result == "default-org"
        mock_repository.organization_create.assert_called_once()

    @patch("api.services.organization_services.create_organization.catalog_settings")
    def test_create_organization_returns_id_only(self, mock_catalog_settings):
        """Test that function returns only the ID, not full response."""
        mock_repository = MagicMock()
        mock_repository.organization_create.return_value = {
            "id": "return-id-test",
            "name": "test",
            "title": "Test",
            "other_field": "value",
        }
        mock_catalog_settings.local_catalog = mock_repository

        result = create_organization(name="test", title="Test", server="local")

        assert result == "return-id-test"
        assert isinstance(result, str)
