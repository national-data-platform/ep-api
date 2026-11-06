# tests/conftest.py
"""Fixtures shared across the test suite."""

from unittest.mock import MagicMock, patch

import pytest

from api.config.swagger_settings import swagger_settings

# The gates each permission level of the Endpoint's group passes.
LEVEL_GATES = {
    "admin": {"admin-area", "editor-area", "viewer-area"},
    "editor": {"editor-area", "viewer-area"},
    "viewer": {"viewer-area"},
    None: set(),
}


class FakeKeycloak:
    """Answers decision requests for the level set with :meth:`grant`."""

    def __init__(self):
        self.granted = set()
        self.asked = []  # (token, gate) per request

    def grant(self, level):
        self.granted = LEVEL_GATES[level]

    def __call__(self, url, headers, data, timeout):
        gate = data["permission"]
        self.asked.append((headers["Authorization"].removeprefix("Bearer "), gate))
        if gate in self.granted:
            return MagicMock(status_code=200, json=lambda: {"result": True})
        return MagicMock(status_code=403, json=lambda: {"error": "access_denied"})


@pytest.fixture
def keycloak():
    """
    Stand in for Keycloak: sets ``AUTHZ_CLIENT_ID`` and refuses every gate
    until the test calls ``keycloak.grant("viewer" | "editor" | "admin")``.
    """
    fake = FakeKeycloak()
    with (
        patch.object(swagger_settings, "authz_client_id", "ep-test"),
        patch("api.services.auth_services.ep_access_gate.requests.post", fake),
    ):
        yield fake
