# tests/test_authorization_service.py
"""
Tests for authorization service functions.
"""
import pytest
from unittest.mock import patch, MagicMock
from fastapi import HTTPException

from api.services.auth_services.authorization_service import (
    check_organization_membership,
    require_organization_member,
    get_user_for_write_operation,
)


class TestCheckOrganizationMembership:
    """Test cases for check_organization_membership function."""

    def test_feature_disabled_always_allows(self):
        """Test that when feature is disabled, always returns True."""
        with patch("api.services.auth_services.authorization_service.swagger_settings") as mock_settings:
            mock_settings.enable_organization_based_access = False

            user_info = {"groups": []}
            result = check_organization_membership(user_info)

            assert result is True

    def test_user_belongs_to_organization_case_insensitive(self):
        """Test user with matching organization (case insensitive)."""
        with patch("api.services.auth_services.authorization_service.swagger_settings") as mock_settings:
            mock_settings.enable_organization_based_access = True
            mock_settings.organization = "TEST-ORG"

            user_info = {"groups": ["test-org", "other-group"]}
            result = check_organization_membership(user_info)

            assert result is True

    def test_user_not_in_organization(self):
        """Test user without matching organization."""
        with patch("api.services.auth_services.authorization_service.swagger_settings") as mock_settings:
            mock_settings.enable_organization_based_access = True
            mock_settings.organization = "REQUIRED-ORG"

            user_info = {"groups": ["other-org", "another-group"]}
            result = check_organization_membership(user_info)

            assert result is False

    def test_user_no_groups(self):
        """Test user with no groups."""
        with patch("api.services.auth_services.authorization_service.swagger_settings") as mock_settings:
            mock_settings.enable_organization_based_access = True
            mock_settings.organization = "REQUIRED-ORG"

            user_info = {"groups": []}
            result = check_organization_membership(user_info)

            assert result is False

    def test_user_groups_missing(self):
        """Test user_info without groups field."""
        with patch("api.services.auth_services.authorization_service.swagger_settings") as mock_settings:
            mock_settings.enable_organization_based_access = True
            mock_settings.organization = "REQUIRED-ORG"

            user_info = {}
            result = check_organization_membership(user_info)

            assert result is False

    def test_user_groups_with_non_string_values(self):
        """Test user groups containing non-string values."""
        with patch("api.services.auth_services.authorization_service.swagger_settings") as mock_settings:
            mock_settings.enable_organization_based_access = True
            mock_settings.organization = "REQUIRED-ORG"

            user_info = {"groups": ["valid-group", 123, None, "required-org"]}
            result = check_organization_membership(user_info)

            assert result is True  # Should find "required-org"


class TestRequireOrganizationMember:
    """Test cases for require_organization_member function."""

    def test_authorized_user_returns_user_info(self):
        """Test that authorized user gets their info returned."""
        with patch("api.services.auth_services.authorization_service.check_organization_membership") as mock_check:
            mock_check.return_value = True

            user_info = {"user_id": "123", "groups": ["test-org"]}
            result = require_organization_member(user_info)

            assert result == user_info
            mock_check.assert_called_once_with(user_info)

    def test_unauthorized_user_raises_403(self):
        """Test that unauthorized user gets 403 Forbidden."""
        with patch("api.services.auth_services.authorization_service.check_organization_membership") as mock_check:
            with patch("api.services.auth_services.authorization_service.swagger_settings") as mock_settings:
                mock_check.return_value = False
                mock_settings.organization = "TEST-ORG"

                user_info = {"user_id": "123", "groups": ["other-org"]}

                with pytest.raises(HTTPException) as exc_info:
                    require_organization_member(user_info)

                assert exc_info.value.status_code == 403
                assert "Access forbidden" in exc_info.value.detail
                assert "TEST-ORG" in exc_info.value.detail


class TestGetUserForWriteOperation:
    """Test cases for get_user_for_write_operation function."""

    def test_feature_enabled_calls_require_organization_member(self):
        """Test that when feature is enabled, it calls require_organization_member."""
        with patch("api.services.auth_services.authorization_service.swagger_settings") as mock_settings:
            with patch("api.services.auth_services.authorization_service.require_organization_member") as mock_require:
                mock_settings.enable_organization_based_access = True
                mock_require.return_value = {"user_id": "123"}

                user_info = {"user_id": "123", "groups": ["test-org"]}
                result = get_user_for_write_operation(user_info)

                assert result == {"user_id": "123"}
                mock_require.assert_called_once_with(user_info)

    def test_feature_disabled_returns_user_directly(self):
        """Test that when feature is disabled, returns user info directly."""
        with patch("api.services.auth_services.authorization_service.swagger_settings") as mock_settings:
            mock_settings.enable_organization_based_access = False

            user_info = {"user_id": "123", "groups": []}
            result = get_user_for_write_operation(user_info)

            assert result == user_info

    def test_feature_enabled_unauthorized_user_raises_403(self):
        """Test that unauthorized user raises 403 when feature is enabled."""
        with patch("api.services.auth_services.authorization_service.swagger_settings") as mock_settings:
            with patch("api.services.auth_services.authorization_service.check_organization_membership") as mock_check:
                mock_settings.enable_organization_based_access = True
                mock_settings.organization = "REQUIRED-ORG"
                mock_check.return_value = False

                user_info = {"user_id": "123", "groups": ["other-org"]}

                with pytest.raises(HTTPException) as exc_info:
                    get_user_for_write_operation(user_info)

                assert exc_info.value.status_code == 403
