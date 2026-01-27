# tests/test_authorization_service.py
"""
Tests for authorization service functions.
"""

import pytest
from unittest.mock import patch, MagicMock
from fastapi import HTTPException

from api.services.auth_services.authorization_service import (
    check_group_membership,
    get_allowed_groups,
    normalize_group_path,
    require_group_member,
    get_user_for_write_operation,
)


class TestNormalizeGroupPath:
    """Test cases for normalize_group_path function."""

    def test_strips_leading_slash(self):
        """Test that leading slash is stripped."""
        assert normalize_group_path("/ndp_ep/group") == "ndp_ep/group"

    def test_strips_trailing_slash(self):
        """Test that trailing slash is stripped."""
        assert normalize_group_path("ndp_ep/group/") == "ndp_ep/group"

    def test_strips_both_slashes(self):
        """Test that both leading and trailing slashes are stripped."""
        assert normalize_group_path("/ndp_ep/group/") == "ndp_ep/group"

    def test_converts_to_lowercase(self):
        """Test that path is converted to lowercase."""
        assert normalize_group_path("/NDP_EP/Group") == "ndp_ep/group"

    def test_strips_whitespace(self):
        """Test that whitespace is stripped."""
        assert normalize_group_path("  /ndp_ep/group  ") == "ndp_ep/group"

    def test_preserves_internal_slashes(self):
        """Test that internal slashes are preserved."""
        assert normalize_group_path("/a/b/c/d") == "a/b/c/d"


class TestGetAllowedGroups:
    """Test cases for get_allowed_groups function."""

    def test_empty_group_names_returns_empty_list(self):
        """Test that empty group_names returns empty list."""
        with patch(
            "api.services.auth_services.authorization_service.swagger_settings"
        ) as mock_settings:
            mock_settings.group_names = ""
            result = get_allowed_groups()
            assert result == []

    def test_single_group(self):
        """Test parsing single group."""
        with patch(
            "api.services.auth_services.authorization_service.swagger_settings"
        ) as mock_settings:
            mock_settings.group_names = "admins"
            result = get_allowed_groups()
            assert result == ["admins"]

    def test_multiple_groups(self):
        """Test parsing multiple groups."""
        with patch(
            "api.services.auth_services.authorization_service.swagger_settings"
        ) as mock_settings:
            mock_settings.group_names = "admins,developers,testers"
            result = get_allowed_groups()
            assert result == ["admins", "developers", "testers"]

    def test_groups_with_spaces_are_trimmed(self):
        """Test that groups with spaces are trimmed."""
        with patch(
            "api.services.auth_services.authorization_service.swagger_settings"
        ) as mock_settings:
            mock_settings.group_names = " admins , developers , testers "
            result = get_allowed_groups()
            assert result == ["admins", "developers", "testers"]

    def test_groups_are_lowercase(self):
        """Test that groups are converted to lowercase."""
        with patch(
            "api.services.auth_services.authorization_service.swagger_settings"
        ) as mock_settings:
            mock_settings.group_names = "ADMINS,Developers,TESTERS"
            result = get_allowed_groups()
            assert result == ["admins", "developers", "testers"]

    def test_empty_entries_are_filtered(self):
        """Test that empty entries are filtered out."""
        with patch(
            "api.services.auth_services.authorization_service.swagger_settings"
        ) as mock_settings:
            mock_settings.group_names = "admins,,developers,,"
            result = get_allowed_groups()
            assert result == ["admins", "developers"]

    def test_leading_slashes_are_stripped(self):
        """Test that leading slashes are stripped from group names."""
        with patch(
            "api.services.auth_services.authorization_service.swagger_settings"
        ) as mock_settings:
            mock_settings.group_names = "/ndp_ep/ep-123,/ndp_ep/ep-456"
            result = get_allowed_groups()
            assert result == ["ndp_ep/ep-123", "ndp_ep/ep-456"]


class TestCheckGroupMembership:
    """Test cases for check_group_membership function."""

    def test_feature_disabled_always_allows(self):
        """Test that when feature is disabled, always returns True."""
        with patch(
            "api.services.auth_services.authorization_service.swagger_settings"
        ) as mock_settings:
            mock_settings.enable_group_based_access = False

            user_info = {"groups": []}
            result = check_group_membership(user_info)

            assert result is True

    def test_no_groups_configured_denies_access(self):
        """Test that when no groups are configured, access is denied."""
        with patch(
            "api.services.auth_services.authorization_service.swagger_settings"
        ) as mock_settings:
            mock_settings.enable_group_based_access = True
            mock_settings.group_names = ""

            user_info = {"groups": ["some-group"]}
            result = check_group_membership(user_info)

            assert result is False

    def test_user_belongs_to_allowed_group_case_insensitive(self):
        """Test user with matching group (case insensitive)."""
        with patch(
            "api.services.auth_services.authorization_service.swagger_settings"
        ) as mock_settings:
            mock_settings.enable_group_based_access = True
            mock_settings.group_names = "ADMINS,developers"

            user_info = {"groups": ["Admins", "other-group"]}
            result = check_group_membership(user_info)

            assert result is True

    def test_user_not_in_any_allowed_group(self):
        """Test user without matching group."""
        with patch(
            "api.services.auth_services.authorization_service.swagger_settings"
        ) as mock_settings:
            mock_settings.enable_group_based_access = True
            mock_settings.group_names = "admins,developers"

            user_info = {"groups": ["other-org", "another-group"]}
            result = check_group_membership(user_info)

            assert result is False

    def test_user_no_groups(self):
        """Test user with no groups."""
        with patch(
            "api.services.auth_services.authorization_service.swagger_settings"
        ) as mock_settings:
            mock_settings.enable_group_based_access = True
            mock_settings.group_names = "admins"

            user_info = {"groups": []}
            result = check_group_membership(user_info)

            assert result is False

    def test_user_groups_missing(self):
        """Test user_info without groups field."""
        with patch(
            "api.services.auth_services.authorization_service.swagger_settings"
        ) as mock_settings:
            mock_settings.enable_group_based_access = True
            mock_settings.group_names = "admins"

            user_info = {}
            result = check_group_membership(user_info)

            assert result is False

    def test_user_groups_with_non_string_values(self):
        """Test user groups containing non-string values."""
        with patch(
            "api.services.auth_services.authorization_service.swagger_settings"
        ) as mock_settings:
            mock_settings.enable_group_based_access = True
            mock_settings.group_names = "admins,developers"

            user_info = {"groups": ["valid-group", 123, None, "developers"]}
            result = check_group_membership(user_info)

            assert result is True  # Should find "developers"

    def test_user_in_one_of_multiple_allowed_groups(self):
        """Test user that belongs to one of several allowed groups."""
        with patch(
            "api.services.auth_services.authorization_service.swagger_settings"
        ) as mock_settings:
            mock_settings.enable_group_based_access = True
            mock_settings.group_names = "admins,developers,testers"

            user_info = {"groups": ["testers"]}
            result = check_group_membership(user_info)

            assert result is True

    def test_user_group_path_with_leading_slash_matches(self):
        """Test user group with leading slash matches config without slash."""
        with patch(
            "api.services.auth_services.authorization_service.swagger_settings"
        ) as mock_settings:
            mock_settings.enable_group_based_access = True
            mock_settings.group_names = "ndp_ep/ep-123"

            # User group as dict with path having leading slash
            user_info = {
                "groups": [{"id": "abc", "name": "ep-123", "path": "/ndp_ep/ep-123"}]
            }
            result = check_group_membership(user_info)

            assert result is True

    def test_config_group_with_leading_slash_matches_user_without(self):
        """Test config group with leading slash matches user group without."""
        with patch(
            "api.services.auth_services.authorization_service.swagger_settings"
        ) as mock_settings:
            mock_settings.enable_group_based_access = True
            mock_settings.group_names = "/ndp_ep/ep-123"

            user_info = {
                "groups": [{"id": "abc", "name": "ep-123", "path": "ndp_ep/ep-123"}]
            }
            result = check_group_membership(user_info)

            assert result is True


class TestRequireGroupMember:
    """Test cases for require_group_member function."""

    def test_authorized_user_returns_user_info(self):
        """Test that authorized user gets their info returned."""
        with patch(
            "api.services.auth_services.authorization_service.check_group_membership"
        ) as mock_check:
            mock_check.return_value = True

            user_info = {"user_id": "123", "groups": ["admins"]}
            result = require_group_member(user_info)

            assert result == user_info
            mock_check.assert_called_once_with(user_info)

    def test_unauthorized_user_raises_403(self):
        """Test that unauthorized user gets 403 Forbidden."""
        with patch(
            "api.services.auth_services.authorization_service.check_group_membership"
        ) as mock_check:
            with patch(
                "api.services.auth_services.authorization_service.swagger_settings"
            ) as mock_settings:
                mock_check.return_value = False
                mock_settings.group_names = "admins,developers"

                user_info = {"user_id": "123", "groups": ["other-org"]}

                with pytest.raises(HTTPException) as exc_info:
                    require_group_member(user_info)

                assert exc_info.value.status_code == 403
                assert "Access forbidden" in exc_info.value.detail


class TestGetUserForWriteOperation:
    """Test cases for get_user_for_write_operation function."""

    def test_feature_enabled_calls_require_group_member(self):
        """Test that when feature is enabled, it calls require_group_member."""
        with patch(
            "api.services.auth_services.authorization_service.swagger_settings"
        ) as mock_settings:
            with patch(
                "api.services.auth_services.authorization_service.require_group_member"
            ) as mock_require:
                mock_settings.enable_group_based_access = True
                mock_require.return_value = {"user_id": "123"}

                user_info = {"user_id": "123", "groups": ["admins"]}
                result = get_user_for_write_operation(user_info)

                assert result == {"user_id": "123"}
                mock_require.assert_called_once_with(user_info)

    def test_feature_disabled_returns_user_directly(self):
        """Test that when feature is disabled, returns user info directly."""
        with patch(
            "api.services.auth_services.authorization_service.swagger_settings"
        ) as mock_settings:
            mock_settings.enable_group_based_access = False

            user_info = {"user_id": "123", "groups": []}
            result = get_user_for_write_operation(user_info)

            assert result == user_info

    def test_feature_enabled_unauthorized_user_raises_403(self):
        """Test that unauthorized user raises 403 when feature is enabled."""
        with patch(
            "api.services.auth_services.authorization_service.swagger_settings"
        ) as mock_settings:
            with patch(
                "api.services.auth_services.authorization_service.check_group_membership"
            ) as mock_check:
                mock_settings.enable_group_based_access = True
                mock_settings.group_names = "admins"
                mock_check.return_value = False

                user_info = {"user_id": "123", "groups": ["other-org"]}

                with pytest.raises(HTTPException) as exc_info:
                    get_user_for_write_operation(user_info)

                assert exc_info.value.status_code == 403
