# tests/test_require_admin.py
"""
Tests for require_admin and is_admin authorization helpers.
"""

from unittest.mock import patch

import pytest
from fastapi import HTTPException

from api.services.auth_services.authorization_service import (
    ADMIN_ROLE_NAME,
    endpoint_admin_role_name,
    is_admin,
    require_admin,
)


class TestEndpointAdminRoleName:
    """Test cases for endpoint_admin_role_name helper."""

    @patch("api.services.auth_services.authorization_service.affinities_settings")
    def test_returns_suffixed_role_when_uuid_configured(self, mock_affinities):
        mock_affinities.ep_uuid = "abc-123"
        assert endpoint_admin_role_name() == "abc-123_admin"

    @patch("api.services.auth_services.authorization_service.affinities_settings")
    def test_returns_empty_when_uuid_missing(self, mock_affinities):
        mock_affinities.ep_uuid = ""
        assert endpoint_admin_role_name() == ""

    @patch("api.services.auth_services.authorization_service.affinities_settings")
    def test_strips_whitespace_in_uuid(self, mock_affinities):
        mock_affinities.ep_uuid = "   abc-123  "
        assert endpoint_admin_role_name() == "abc-123_admin"


class TestIsAdmin:
    """Test cases for is_admin helper."""

    @patch("api.services.auth_services.authorization_service.affinities_settings")
    def test_ndp_admin_role_is_admin(self, mock_affinities):
        mock_affinities.ep_uuid = "some-uuid"
        assert is_admin({"roles": [ADMIN_ROLE_NAME]}) is True

    @patch("api.services.auth_services.authorization_service.affinities_settings")
    def test_endpoint_admin_role_is_admin(self, mock_affinities):
        mock_affinities.ep_uuid = "some-uuid"
        assert is_admin({"roles": ["some-uuid_admin"]}) is True

    @patch("api.services.auth_services.authorization_service.affinities_settings")
    def test_case_insensitive_match(self, mock_affinities):
        mock_affinities.ep_uuid = "Some-UUID"
        assert is_admin({"roles": ["some-uuid_ADMIN"]}) is True

    @patch("api.services.auth_services.authorization_service.affinities_settings")
    def test_regular_role_is_not_admin(self, mock_affinities):
        mock_affinities.ep_uuid = "some-uuid"
        assert is_admin({"roles": ["default-roles-ndp"]}) is False

    @patch("api.services.auth_services.authorization_service.affinities_settings")
    def test_missing_roles_is_not_admin(self, mock_affinities):
        mock_affinities.ep_uuid = "some-uuid"
        assert is_admin({}) is False

    @patch("api.services.auth_services.authorization_service.affinities_settings")
    def test_non_list_roles_is_not_admin(self, mock_affinities):
        mock_affinities.ep_uuid = "some-uuid"
        assert is_admin({"roles": "ndp_admin"}) is False

    @patch("api.services.auth_services.authorization_service.affinities_settings")
    def test_empty_uuid_still_accepts_ndp_admin(self, mock_affinities):
        mock_affinities.ep_uuid = ""
        assert is_admin({"roles": [ADMIN_ROLE_NAME]}) is True

    @patch("api.services.auth_services.authorization_service.affinities_settings")
    def test_empty_uuid_rejects_endpoint_admin_pretender(self, mock_affinities):
        # Without a UUID there is no "{uuid}_admin" role to validate against
        mock_affinities.ep_uuid = ""
        assert is_admin({"roles": ["_admin"]}) is False


class TestRequireAdmin:
    """Test cases for the require_admin FastAPI dependency."""

    @patch("api.services.auth_services.authorization_service.affinities_settings")
    def test_admin_user_returns_user_info(self, mock_affinities):
        mock_affinities.ep_uuid = "some-uuid"
        user_info = {"sub": "s", "username": "raul", "roles": [ADMIN_ROLE_NAME]}
        assert require_admin(user_info) is user_info

    @patch("api.services.auth_services.authorization_service.affinities_settings")
    def test_endpoint_admin_user_returns_user_info(self, mock_affinities):
        mock_affinities.ep_uuid = "some-uuid"
        user_info = {
            "sub": "s",
            "username": "u",
            "roles": ["some-uuid_admin"],
        }
        assert require_admin(user_info) is user_info

    @patch("api.services.auth_services.authorization_service.affinities_settings")
    def test_non_admin_user_raises_403(self, mock_affinities):
        mock_affinities.ep_uuid = "some-uuid"
        user_info = {"sub": "s", "username": "yutian", "roles": ["user"]}
        with pytest.raises(HTTPException) as exc_info:
            require_admin(user_info)
        assert exc_info.value.status_code == 403
        assert "Administrator role required" in exc_info.value.detail
