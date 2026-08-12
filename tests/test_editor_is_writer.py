"""
The write tier is named "editor" by the identity provider, so an endpoint
editor must be recognized as a writer (issue #236). Uses the exact role form
Keycloak emits: group:ndp_ep/ep-{id}:editor.
"""

from unittest.mock import patch

from api.services.auth_services.authorization_service import (
    effective_role,
    is_writer,
)

EDITOR = {
    "roles": ["group:ndp_ep/ep-699a85d3f2e23b17ce85c2b7:editor"],
    "groups": [],
    "sub": "u-editor",
}


def _ctx():
    s = patch("api.services.auth_services.authorization_service.swagger_settings")
    a = patch("api.services.auth_services.authorization_service.affinities_settings")
    return s, a


def test_endpoint_editor_is_a_writer():
    s, a = _ctx()
    with s as sett, a as aff:
        sett.group_names = "ndp_ep/ep-699a85d3f2e23b17ce85c2b7"
        aff.ep_uuid = ""
        assert is_writer(EDITOR) is True
        assert effective_role(EDITOR) == "writer"


def test_platform_ndp_editor_is_a_writer():
    s, a = _ctx()
    with s as sett, a as aff:
        sett.group_names = ""
        aff.ep_uuid = ""
        assert is_writer({"roles": ["ndp_editor"]}) is True


def test_a_plain_viewer_is_not_a_writer():
    s, a = _ctx()
    with s as sett, a as aff:
        sett.group_names = "ndp_ep/ep-699a85d3f2e23b17ce85c2b7"
        aff.ep_uuid = ""
        viewer = {"roles": ["group:ndp_ep/ep-699a85d3f2e23b17ce85c2b7:viewer"]}
        assert is_writer(viewer) is False
        assert effective_role(viewer) == "viewer"
