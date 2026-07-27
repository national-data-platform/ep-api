"""
Regression: an endpoint admin whose role uses the Keycloak group path
(group:ndp_ep/ep-{id}:admin) must be recognized, even when AFFINITIES_EP_UUID
is unset — the case reported for nlr.ndp.utah.edu.
"""

from unittest.mock import patch

from api.services.auth_services.authorization_service import effective_role, is_admin

# The exact role from the reported /information response.
SALEEM = {
    "roles": [
        "group:jhub_user:editor",
        "professor",
        "group:ndp_ep/ep-6a619d3f8b9242b94b015efb:admin",
        "default-roles-ndp",
    ],
    "groups": [],
    "sub": "77201bf0-329e-47e9-813a-a67ec967fdb1",
    "username": "saleem.alharir@utah.edu",
}


def test_group_path_admin_is_recognized_without_affinities_uuid():
    with (
        patch("api.services.auth_services.authorization_service.swagger_settings") as s,
        patch(
            "api.services.auth_services.authorization_service.affinities_settings"
        ) as a,
    ):
        s.group_names = "ndp_ep/ep-6a619d3f8b9242b94b015efb"
        a.ep_uuid = ""  # the Federation/installer case
        assert is_admin(SALEEM) is True
        assert effective_role(SALEEM) == "admin"


def test_leading_slash_in_group_path_still_matches():
    slashed = {"roles": ["group:/ndp_ep/ep-abc:admin"]}
    with (
        patch("api.services.auth_services.authorization_service.swagger_settings") as s,
        patch(
            "api.services.auth_services.authorization_service.affinities_settings"
        ) as a,
    ):
        s.group_names = "ndp_ep/ep-abc"
        a.ep_uuid = ""
        assert is_admin(slashed) is True
