"""
Endpoint clients without permission gates (issue #433).

Only clients created by Federation 2.0.0 or later, or adopted, have the
``admin-area``/``editor-area``/``viewer-area`` gates. Keycloak answers any
other client with 400 "Client does not support permissions" (checked
against Keycloak 26.5.1). Such an Endpoint decides from the user's roles, as
before the gates, instead of refusing everyone; a client with gates is still
decided by Keycloak alone.
"""

from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from api.config.swagger_settings import swagger_settings
from api.routes.user_routes.user_info import get_user_info
from api.services.auth_services.ep_access_gate import (
    ep_access_gate,
    ep_admin_gate,
    ep_editor_gate,
    ep_viewer_gate,
)

POST = "api.services.auth_services.ep_access_gate.requests.post"
TOKEN = MagicMock(credentials="user-token")
GROUP = "ndp_ep/ep-6ae0f828"

NO_PERMISSIONS = (
    400,
    {
        "error": "invalid_request",
        "error_description": "Client does not support permissions",
    },
)
NO_GATE = (
    400,
    {
        "error": "invalid_resource",
        "error_description": "Resource with id [admin-area] does not exist.",
    },
)


@pytest.fixture(autouse=True)
def _settings():
    with (
        patch.object(swagger_settings, "oidc_service_client_id", "ep-6ae0f828"),
        patch.object(swagger_settings, "group_names", ""),
        patch.object(swagger_settings, "authz_realm", "NDP"),
        patch.object(swagger_settings, "keycloak_url", "https://idp.example.org"),
        patch.object(swagger_settings, "test_token", ""),
    ):
        yield


def _keycloak(status_code, payload):
    response = MagicMock(status_code=status_code)
    response.json.return_value = payload
    return patch(POST, return_value=response)


def _user(*roles, groups=()):
    return {
        "sub": "u-1",
        "username": "alice",
        "roles": list(roles),
        "groups": list(groups),
    }


def _passes(dependency, user):
    try:
        dependency(user, TOKEN)
        return True
    except HTTPException as exc:
        assert exc.status_code == 403
        return False


GATES = (ep_admin_gate, ep_editor_gate, ep_viewer_gate)


@pytest.mark.parametrize("answer", [NO_PERMISSIONS, NO_GATE])
@pytest.mark.parametrize(
    "user,expected",
    [
        (_user("ndp_admin"), (True, True, True)),
        (_user(f"group:{GROUP}:admin"), (True, True, True)),
        (_user(f"group:/{GROUP}:editor"), (False, True, True)),
        (_user(f"group:{GROUP}:writer"), (False, True, True)),
        (_user("ndp_writer"), (False, True, True)),
        (_user(f"group:{GROUP}:viewer"), (False, False, True)),
        (_user(groups=[f"/{GROUP}"]), (False, False, True)),
        (_user(groups=[{"path": f"/{GROUP}/viewers"}]), (False, False, True)),
        (_user(), (False, False, False)),
        # Roles on another Endpoint's group count for nothing here.
        (
            _user("group:ndp_ep/ep-other:admin", groups=["/ndp_ep/ep-other"]),
            (False, False, False),
        ),
    ],
)
def test_a_client_without_gates_is_decided_from_the_roles(answer, user, expected):
    with _keycloak(*answer):
        assert tuple(_passes(gate, user) for gate in GATES) == expected


def test_group_names_still_name_the_endpoint_group():
    with (
        patch.object(swagger_settings, "group_names", "ndp_ep/legacy-group"),
        _keycloak(*NO_PERMISSIONS),
    ):
        assert _passes(ep_editor_gate, _user("group:ndp_ep/legacy-group:editor"))


@pytest.mark.parametrize(
    "answer,granted",
    [((200, {"result": True}), True), ((403, {"error": "access_denied"}), False)],
)
def test_a_client_with_gates_is_decided_by_keycloak_alone(answer, granted):
    """Roles grant nothing once the client has gates: an admin role with a
    denial is refused, no role with a grant passes."""
    with _keycloak(*answer):
        assert _passes(ep_admin_gate, _user("ndp_admin")) is granted
        assert _passes(ep_admin_gate, _user()) is granted


def test_without_the_user_a_client_without_gates_refuses():
    with _keycloak(*NO_PERMISSIONS), pytest.raises(HTTPException) as refused:
        ep_access_gate("user-token", "viewer-area")
    assert refused.value.status_code == 403


def test_other_400s_are_still_refusals():
    """An unknown client is a misconfiguration, not an old client."""
    with _keycloak(
        400,
        {
            "error": "invalid_request",
            "error_description": "Unknown resource server id: [x]",
        },
    ):
        assert not _passes(ep_viewer_gate, _user("ndp_admin"))


@pytest.mark.parametrize(
    "user,role",
    [
        (_user(f"group:{GROUP}:admin"), "admin"),
        (_user(f"group:{GROUP}:editor"), "writer"),
        (_user(groups=[f"/{GROUP}"]), "viewer"),
    ],
)
def test_user_info_reports_the_role_from_the_roles(user, role):
    with _keycloak(*NO_PERMISSIONS):
        assert get_user_info(user, TOKEN)["effective_role"] == role


def test_user_info_refuses_a_stranger():
    with _keycloak(*NO_PERMISSIONS), pytest.raises(HTTPException) as refused:
        get_user_info(_user(), TOKEN)
    assert refused.value.status_code == 403
