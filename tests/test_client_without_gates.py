"""
Endpoint clients without permission gates (issue #441).

Only clients created by Federation 2.0.0 or later, or adopted, have the
``admin-area``/``editor-area``/``viewer-area`` gates. Keycloak answers any
other client with 400 "Client does not support permissions" (or
``invalid_resource`` when a gate is missing). Since every client has been
adopted, the Endpoint no longer falls back to the user's realm roles (the
compatibility shim of #433 is gone): such a client refuses everyone, and the
log says once that the client has to be adopted.
"""

import importlib
import logging
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from api.config.swagger_settings import swagger_settings
from api.routes.user_routes.user_info import get_user_info
from api.services.auth_services.ep_access_gate import (
    ep_admin_gate,
    ep_editor_gate,
    ep_viewer_gate,
)

POST = "api.services.auth_services.ep_access_gate.requests.post"
# The package re-exports the function under the module's name.
gate_module = importlib.import_module("api.services.auth_services.ep_access_gate")
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
        patch.object(gate_module, "_warned_no_gates", False),
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
    "user",
    [
        _user("ndp_admin"),
        _user(f"group:{GROUP}:admin"),
        _user("ndp_writer"),
        _user(f"group:{GROUP}:viewer"),
        _user(groups=[f"/{GROUP}"]),
    ],
)
def test_realm_roles_no_longer_open_a_client_without_gates(answer, user):
    """The roles that passed before the gates (#433) now pass nothing."""
    with _keycloak(*answer):
        assert [_passes(gate, user) for gate in GATES] == [False, False, False]


def test_a_client_without_gates_is_logged_once_as_needing_adoption(caplog):
    with _keycloak(*NO_PERMISSIONS), caplog.at_level(logging.ERROR):
        for gate in GATES:
            _passes(gate, _user("ndp_admin"))
    messages = [r.getMessage() for r in caplog.records if r.levelno >= logging.ERROR]
    assert len(messages) == 1
    assert "ep-6ae0f828" in messages[0]
    assert "has no permission gates" in messages[0]
    assert "adopt" in messages[0]


@pytest.mark.parametrize(
    "answer,granted",
    [((200, {"result": True}), True), ((403, {"error": "access_denied"}), False)],
)
def test_a_client_with_gates_is_decided_by_keycloak_alone(answer, granted):
    """Roles grant nothing: an admin role with a denial is refused, no role
    with a grant passes."""
    with _keycloak(*answer):
        assert _passes(ep_admin_gate, _user("ndp_admin")) is granted
        assert _passes(ep_admin_gate, _user()) is granted


def test_user_info_refuses_everyone_on_a_client_without_gates():
    with _keycloak(*NO_PERMISSIONS), pytest.raises(HTTPException) as refused:
        get_user_info(_user("ndp_admin"), TOKEN)
    assert refused.value.status_code == 403


def test_the_shim_module_is_gone():
    with pytest.raises(ImportError):
        from api.services.auth_services import legacy_roles  # noqa: F401
