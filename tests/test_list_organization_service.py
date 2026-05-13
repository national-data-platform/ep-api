# tests/test_list_organization_service.py
"""
Tests for list_organization service.
"""

import pytest
from unittest.mock import MagicMock, patch

from api.services.organization_services.list_organization import list_organization


class TestListOrganization:
    """Test cases for list_organization function."""

    @patch("api.services.organization_services.list_organization.catalog_settings")
    def test_list_organization_global_server(self, mock_catalog_settings):
        """Test listing organizations from global server."""
        mock_repository = MagicMock()
        mock_repository.organization_list.return_value = ["org1", "org2", "org3"]
        mock_catalog_settings.global_catalog = mock_repository

        result = list_organization(server="global")

        assert result == ["org1", "org2", "org3"]
        mock_repository.organization_list.assert_called_once_with(all_fields=False)

    @patch("api.services.organization_services.list_organization.catalog_settings")
    def test_list_organization_local_server(self, mock_catalog_settings):
        """Test listing organizations from local server."""
        mock_repository = MagicMock()
        mock_repository.organization_list.return_value = ["local-org1", "local-org2"]
        mock_catalog_settings.local_catalog = mock_repository

        result = list_organization(server="local")

        assert result == ["local-org1", "local-org2"]
        mock_repository.organization_list.assert_called_once_with(all_fields=False)

    @patch("api.services.organization_services.list_organization.catalog_settings")
    def test_list_organization_pre_ckan_server(self, mock_catalog_settings):
        """Test listing organizations from pre_ckan server."""
        mock_repository = MagicMock()
        mock_repository.organization_list.return_value = ["pre-org1", "pre-org2"]
        mock_catalog_settings.pre_catalog = mock_repository

        result = list_organization(server="pre_ckan")

        assert result == ["pre-org1", "pre-org2"]
        mock_repository.organization_list.assert_called_once_with(all_fields=False)

    @patch("api.services.organization_services.list_organization.catalog_settings")
    def test_list_organization_with_name_filter(self, mock_catalog_settings):
        """Test filtering organizations by name."""
        mock_repository = MagicMock()
        mock_repository.organization_list.return_value = [
            "test-org",
            "production-org",
            "test-api",
            "development",
        ]
        mock_catalog_settings.global_catalog = mock_repository

        result = list_organization(name="test", server="global")

        assert result == ["test-org", "test-api"]

    @patch("api.services.organization_services.list_organization.catalog_settings")
    def test_list_organization_case_insensitive_filter(self, mock_catalog_settings):
        """Test that name filter is case-insensitive."""
        mock_repository = MagicMock()
        mock_repository.organization_list.return_value = [
            "TestOrg",
            "PRODUCTION",
            "testApi",
            "Development",
        ]
        mock_catalog_settings.global_catalog = mock_repository

        result = list_organization(name="TEST", server="global")

        assert result == ["TestOrg", "testApi"]

    @patch("api.services.organization_services.list_organization.catalog_settings")
    def test_list_organization_no_matches(self, mock_catalog_settings):
        """Test filtering with no matches returns empty list."""
        mock_repository = MagicMock()
        mock_repository.organization_list.return_value = ["org1", "org2", "org3"]
        mock_catalog_settings.global_catalog = mock_repository

        result = list_organization(name="nonexistent", server="global")

        assert result == []

    @patch("api.services.organization_services.list_organization.catalog_settings")
    def test_list_organization_default_server(self, mock_catalog_settings):
        """Test that default server is 'global'."""
        mock_repository = MagicMock()
        mock_repository.organization_list.return_value = ["default-org"]
        mock_catalog_settings.global_catalog = mock_repository

        result = list_organization()

        assert result == ["default-org"]
        mock_repository.organization_list.assert_called_once_with(all_fields=False)

    @patch("api.services.organization_services.list_organization.catalog_settings")
    def test_list_organization_unrecognized_server_uses_local(
        self, mock_catalog_settings
    ):
        """Test that unrecognized server defaults to local."""
        mock_repository = MagicMock()
        mock_repository.organization_list.return_value = ["local-org"]
        mock_catalog_settings.local_catalog = mock_repository

        result = list_organization(server="unknown")

        assert result == ["local-org"]
        mock_repository.organization_list.assert_called_once_with(all_fields=False)

    @patch("api.services.organization_services.list_organization.catalog_settings")
    def test_list_organization_error_handling(self, mock_catalog_settings):
        """Test error handling when repository fails."""
        mock_repository = MagicMock()
        mock_repository.organization_list.side_effect = Exception("Connection failed")
        mock_catalog_settings.global_catalog = mock_repository

        with pytest.raises(Exception) as exc_info:
            list_organization(server="global")

        assert "Error retrieving list of organizations" in str(exc_info.value)
        assert "Connection failed" in str(exc_info.value)

    @patch("api.services.organization_services.list_organization.catalog_settings")
    def test_list_organization_empty_list(self, mock_catalog_settings):
        """Test handling of empty organization list."""
        mock_repository = MagicMock()
        mock_repository.organization_list.return_value = []
        mock_catalog_settings.global_catalog = mock_repository

        result = list_organization(server="global")

        assert result == []

    @patch("api.services.organization_services.list_organization.catalog_settings")
    def test_list_organization_partial_name_match(self, mock_catalog_settings):
        """Test that partial name matching works."""
        mock_repository = MagicMock()
        mock_repository.organization_list.return_value = [
            "my-organization",
            "your-organization",
            "their-team",
        ]
        mock_catalog_settings.global_catalog = mock_repository

        result = list_organization(name="organization", server="global")

        assert result == ["my-organization", "your-organization"]

    @patch("api.services.organization_services.list_organization.catalog_settings")
    def test_list_organization_with_user_hash_mongo_shape(self, mock_catalog_settings):
        """When user_hash is set, MongoDB-style docs are filtered by their top-level ndp_user_id."""
        mock_repository = MagicMock()
        mock_repository.organization_list.return_value = [
            {"name": "alpha", "ndp_user_id": "abc1234567890def"},
            {"name": "beta", "ndp_user_id": "deadbeefcafef00d"},
            {"name": "gamma"},  # legacy org with no creator hash
        ]
        mock_catalog_settings.global_catalog = mock_repository

        result = list_organization(server="global", user_hash="abc1234567890def")

        assert result == ["alpha"]
        mock_repository.organization_list.assert_called_once_with(
            all_fields=True, include_extras=True
        )

    @patch("api.services.organization_services.list_organization.catalog_settings")
    def test_list_organization_with_user_hash_ckan_shape(self, mock_catalog_settings):
        """When user_hash is set, CKAN-style docs are filtered by the ndp_user_id extra."""
        mock_repository = MagicMock()
        mock_repository.organization_list.return_value = [
            {
                "name": "alpha",
                "extras": [
                    {"key": "ndp_user_id", "value": "abc1234567890def"},
                    {"key": "ndp_creator_md5", "value": "ignored"},
                ],
            },
            {
                "name": "beta",
                "extras": [{"key": "ndp_user_id", "value": "deadbeefcafef00d"}],
            },
            # legacy org: no extras at all
            {"name": "gamma", "extras": []},
        ]
        mock_catalog_settings.global_catalog = mock_repository

        result = list_organization(server="global", user_hash="abc1234567890def")

        assert result == ["alpha"]

    @patch("api.services.organization_services.list_organization.catalog_settings")
    def test_list_organization_with_user_hash_and_name_filter(
        self, mock_catalog_settings
    ):
        """Name filter is applied on top of the creator-hash filter."""
        mock_repository = MagicMock()
        mock_repository.organization_list.return_value = [
            {"name": "alpha-team", "ndp_user_id": "h"},
            {"name": "beta-team", "ndp_user_id": "h"},
            {"name": "alpha-archive", "ndp_user_id": "other"},
        ]
        mock_catalog_settings.global_catalog = mock_repository

        result = list_organization(name="alpha", server="global", user_hash="h")

        assert result == ["alpha-team"]

    @patch("api.services.organization_services.list_organization.catalog_settings")
    def test_list_organization_without_user_hash_does_not_request_extras(
        self, mock_catalog_settings
    ):
        """The pre-existing call shape is preserved when user_hash is not provided."""
        mock_repository = MagicMock()
        mock_repository.organization_list.return_value = ["org1", "org2"]
        mock_catalog_settings.global_catalog = mock_repository

        list_organization(server="global")

        mock_repository.organization_list.assert_called_once_with(all_fields=False)
