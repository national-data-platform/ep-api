"""
The test token must grant full access, including on endpoints that enable
group-based access control.

Regression for the case reported in the field: signing in with the test token
was refused on an endpoint with ``ENABLE_GROUP_BASED_ACCESS=True`` because the
fabricated user carried the role ``admin`` (not the recognized ``ndp_admin``)
and belonged to no groups.
"""

from unittest.mock import patch

from api.services.auth_services.authorization_service import (
    check_group_membership,
    effective_role,
    is_admin,
)
from api.services.auth_services.get_current_user import get_current_user


class _Creds:
    def __init__(self, token):
        self.credentials = token


def _test_user():
    with patch(
        "api.services.auth_services.get_current_user.swagger_settings"
    ) as settings:
        settings.test_token = "the-test-token"
        return get_current_user(token_data=_Creds("the-test-token"))


def test_test_token_is_recognized_as_platform_admin():
    assert is_admin(_test_user()) is True


def test_test_token_resolves_to_admin_effective_role():
    assert effective_role(_test_user()) == "admin"


def test_test_token_passes_group_based_access():
    """
    The core of the reported bug: with group-based access enabled and an
    allowed group configured, the test user (which is in no groups) must still
    be admitted, on the strength of its platform admin role.
    """
    with patch(
        "api.services.auth_services.authorization_service.swagger_settings"
    ) as settings:
        settings.enable_group_based_access = True
        settings.group_names = "ndp_ep/ep-6a4bd3018a4f66a6d25cd511"
        assert check_group_membership(_test_user()) is True
