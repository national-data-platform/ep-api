"""
The test token must grant full access, including on endpoints that enable
group-based access control.

Keycloak cannot decide for a token it never issued, so the permission gates
pass the test token without asking, as get_current_user accepts it without
asking the AAI API.
"""

from unittest.mock import MagicMock, patch

from api.config.swagger_settings import swagger_settings
from api.routes.user_routes.user_info import get_user_info
from api.services.auth_services import (
    ep_admin_gate,
    ep_editor_gate,
    ep_viewer_gate,
    get_current_user,
)

TEST_TOKEN = MagicMock(credentials="the-test-token")


def test_test_token_passes_every_gate_without_asking_keycloak(keycloak):
    with patch.object(swagger_settings, "test_token", "the-test-token"):
        user = get_current_user(token_data=TEST_TOKEN)
        for gate in (ep_admin_gate, ep_editor_gate, ep_viewer_gate):
            assert gate(user, TEST_TOKEN) is user
    assert keycloak.asked == []


def test_test_token_enters_as_admin_without_a_client():
    with (
        patch.object(swagger_settings, "test_token", "the-test-token"),
        patch.object(swagger_settings, "oidc_service_client_id", ""),
    ):
        user = get_current_user(token_data=TEST_TOKEN)
        assert get_user_info(user, TEST_TOKEN)["effective_role"] == "admin"
