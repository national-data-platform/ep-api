# tests/test_ep_access_gate.py
"""
Tests for the permission gates.

``ep_access_gate`` asks Keycloak as the Federation's does: only
``{"result": true}`` grants, Keycloak rejecting the token is 401, Keycloak
failing or unreachable 502. The ``ep_*_gate`` dependencies ask it for their
gate with the caller's token and return the user.
"""

from unittest.mock import MagicMock, patch

import pytest
import requests
from fastapi import HTTPException

from api.config.swagger_settings import swagger_settings
from api.services.auth_services.ep_access_gate import (
    ep_access_gate,
    ep_admin_gate,
    ep_editor_gate,
    ep_viewer_gate,
)

POST = "api.services.auth_services.ep_access_gate.requests.post"
TOKEN = MagicMock(credentials="user-token")

# What the AAI API reports grants nothing: only Keycloak's gates decide.
USER = {"sub": "u-1", "roles": ["ndp_admin"], "groups": ["/ndp_ep/ep-test"]}


@pytest.fixture(autouse=True)
def _settings():
    with (
        patch.object(swagger_settings, "oidc_service_client_id", "ep-6ae0f828"),
        patch.object(swagger_settings, "authz_realm", "NDP"),
        patch.object(swagger_settings, "keycloak_url", "https://idp.example.org"),
        patch.object(swagger_settings, "test_token", "the-test-token"),
    ):
        yield


def _answer(status_code, payload=None):
    response = MagicMock(status_code=status_code)
    if payload is None:
        response.json.side_effect = ValueError("not json")
    else:
        response.json.return_value = payload
    return response


def _status(call):
    with pytest.raises(HTTPException) as exc_info:
        call()
    return exc_info.value.status_code


def _refusal(token="user-token"):
    return _status(lambda: ep_access_gate(token, "viewer-area"))


class TestEpAccessGate:
    def test_asks_the_realm_on_keycloak_url_with_the_callers_token(self):
        with patch(POST, return_value=_answer(200, {"result": True})) as post:
            ep_access_gate("user-token", "editor-area")

        assert post.call_args.args == (
            "https://idp.example.org/realms/NDP/protocol/openid-connect/token",
        )
        assert post.call_args.kwargs["headers"] == {
            "Authorization": "Bearer user-token"
        }
        assert post.call_args.kwargs["data"] == {
            "grant_type": "urn:ietf:params:oauth:grant-type:uma-ticket",
            "audience": "ep-6ae0f828",
            "permission": "editor-area",
            "response_mode": "decision",
        }

    @pytest.mark.parametrize(
        "status_code,payload",
        [
            (403, {"error": "access_denied"}),
            (400, {"error": "invalid_resource"}),  # no such client or gate
            (200, {"result": False}),
            (200, None),
        ],
    )
    def test_anything_but_a_grant_is_403(self, status_code, payload):
        with patch(POST, return_value=_answer(status_code, payload)):
            assert _refusal() == 403

    def test_a_rejected_token_is_401(self):
        with patch(POST, return_value=_answer(401, {"error": "invalid_grant"})):
            assert _refusal() == 401

    def test_keycloak_failing_or_unreachable_is_502(self):
        with patch(POST, return_value=_answer(503)):
            assert _refusal() == 502
        with patch(POST, side_effect=requests.ConnectionError("down")):
            assert _refusal() == 502

    def test_the_test_token_passes_without_asking(self):
        with patch(POST) as post:
            ep_access_gate("the-test-token", "admin-area")
        post.assert_not_called()

    def test_without_a_client_nothing_is_asked_and_the_answer_is_403(self):
        with (
            patch.object(swagger_settings, "oidc_service_client_id", ""),
            patch(POST) as post,
        ):
            assert _refusal() == 403
        post.assert_not_called()


class TestGateDependencies:
    @pytest.mark.parametrize(
        "dependency,gate",
        [
            (ep_admin_gate, "admin-area"),
            (ep_editor_gate, "editor-area"),
            (ep_viewer_gate, "viewer-area"),
        ],
    )
    def test_each_asks_its_gate_with_the_callers_token(
        self, keycloak, dependency, gate
    ):
        keycloak.grant("admin")

        assert dependency(USER, TOKEN) is USER
        assert keycloak.asked == [("user-token", gate)]

    @pytest.mark.parametrize(
        "level,admin,editor,viewer",
        [
            ("admin", True, True, True),
            ("editor", False, True, True),
            ("viewer", False, False, True),
            (None, False, False, False),
        ],
    )
    def test_each_level_passes_its_gates(self, keycloak, level, admin, editor, viewer):
        keycloak.grant(level)

        for dependency, allowed in (
            (ep_admin_gate, admin),
            (ep_editor_gate, editor),
            (ep_viewer_gate, viewer),
        ):
            if allowed:
                assert dependency(USER, TOKEN) is USER
            else:
                assert _status(lambda: dependency(USER, TOKEN)) == 403
