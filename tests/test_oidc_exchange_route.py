# tests/test_oidc_exchange_route.py
"""
Exchanging an identity-provider authorization code on the Endpoint.

The exchange lives here rather than in the browser so that a **confidential**
client can be used: the client a Federation registration creates for an
Endpoint has a secret, and a secret cannot be shipped to a page. These tests
pin the two things that makes possible — the secret is sent to the provider,
and it never comes back out.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from api.main import app

PAYLOAD = {
    "code": "auth-code-from-the-provider",
    "redirect_uri": "https://ep.example.org/ui/auth/callback",
    "code_verifier": "the-pkce-verifier",
}

DISCOVERY = {
    "token_endpoint": "https://idp.example.org/realms/NDP/protocol/openid-connect/token"
}


def _client_returning(token_response, discovery=None):
    """An httpx.AsyncClient double: discovery on GET, the exchange on POST."""
    discovery_response = MagicMock()
    discovery_response.status_code = 200
    discovery_response.json.return_value = discovery or DISCOVERY

    http = AsyncMock()
    http.get = AsyncMock(return_value=discovery_response)
    http.post = AsyncMock(return_value=token_response)
    http.__aenter__ = AsyncMock(return_value=http)
    http.__aexit__ = AsyncMock(return_value=None)
    return http


def _token_response(status_code, body):
    response = MagicMock()
    response.status_code = status_code
    response.content = b"{}"
    response.json.return_value = body
    return response


@pytest.fixture
def client():
    return TestClient(app)


class TestConfidentialClient:
    """The case the feature exists for."""

    @patch("api.routes.user_routes.oidc_exchange.httpx.AsyncClient")
    @patch("api.routes.user_routes.oidc_exchange.oidc_settings")
    def test_the_secret_is_sent_to_the_provider(self, settings, async_client, client):
        settings.is_configured = True
        settings.issuer = "https://idp.example.org/realms/NDP"
        settings.client_id = "ep-6a5e300b"
        settings.client_secret = "the-client-secret"

        http = _client_returning(
            _token_response(200, {"access_token": "issued-token", "expires_in": 300})
        )
        async_client.return_value = http

        response = client.post("/user/oidc/exchange", json=PAYLOAD)

        assert response.status_code == 200
        assert response.json()["access_token"] == "issued-token"

        sent = http.post.call_args.kwargs["data"]
        assert sent["client_secret"] == "the-client-secret"
        assert sent["client_id"] == "ep-6a5e300b"
        assert sent["code_verifier"] == "the-pkce-verifier"
        assert sent["grant_type"] == "authorization_code"

    @patch("api.routes.user_routes.oidc_exchange.httpx.AsyncClient")
    @patch("api.routes.user_routes.oidc_exchange.oidc_settings")
    def test_the_secret_never_reaches_the_caller(self, settings, async_client, client):
        settings.is_configured = True
        settings.issuer = "https://idp.example.org/realms/NDP"
        settings.client_id = "ep-6a5e300b"
        settings.client_secret = "the-client-secret"

        async_client.return_value = _client_returning(
            _token_response(
                200,
                {
                    "access_token": "issued-token",
                    # A provider that echoed the secret back must not get it
                    # forwarded to the browser either.
                    "client_secret": "the-client-secret",
                    "refresh_token": "refresh-token",
                },
            )
        )

        response = client.post("/user/oidc/exchange", json=PAYLOAD)

        assert response.status_code == 200
        assert "the-client-secret" not in response.text
        assert "refresh_token" not in response.json()


class TestPublicClient:
    """A public client goes through the same route with no secret."""

    @patch("api.routes.user_routes.oidc_exchange.httpx.AsyncClient")
    @patch("api.routes.user_routes.oidc_exchange.oidc_settings")
    def test_no_client_authentication_is_sent(self, settings, async_client, client):
        settings.is_configured = True
        settings.issuer = "https://idp.example.org/realms/NDP"
        settings.client_id = "ndp-ep-ui"
        settings.client_secret = ""

        http = _client_returning(_token_response(200, {"access_token": "issued-token"}))
        async_client.return_value = http

        response = client.post("/user/oidc/exchange", json=PAYLOAD)

        assert response.status_code == 200
        assert "client_secret" not in http.post.call_args.kwargs["data"]


class TestFailures:
    """What the user is told when it does not work."""

    @patch("api.routes.user_routes.oidc_exchange.oidc_settings")
    def test_unconfigured_endpoint_says_so(self, settings, client):
        settings.is_configured = False

        response = client.post("/user/oidc/exchange", json=PAYLOAD)

        assert response.status_code == 503
        assert "not configured" in response.json()["detail"].lower()

    @patch("api.routes.user_routes.oidc_exchange.httpx.AsyncClient")
    @patch("api.routes.user_routes.oidc_exchange.oidc_settings")
    def test_the_providers_own_wording_is_passed_on(
        self, settings, async_client, client
    ):
        """
        'Invalid client or Invalid client credentials' is what a confidential
        client answers when no secret is sent. Rewriting it would hide the one
        clue that says the client, not the user, is misconfigured.
        """
        settings.is_configured = True
        settings.issuer = "https://idp.example.org/realms/NDP"
        settings.client_id = "ep-6a5e300b"
        settings.client_secret = ""

        async_client.return_value = _client_returning(
            _token_response(
                401,
                {
                    "error": "unauthorized_client",
                    "error_description": "Invalid client or Invalid client credentials",
                },
            )
        )

        response = client.post("/user/oidc/exchange", json=PAYLOAD)

        assert response.status_code == 400
        assert "Invalid client" in response.json()["detail"]

    @patch("api.routes.user_routes.oidc_exchange.httpx.AsyncClient")
    @patch("api.routes.user_routes.oidc_exchange.oidc_settings")
    def test_an_unreachable_provider_is_a_502(self, settings, async_client, client):
        settings.is_configured = True
        settings.issuer = "https://idp.example.org/realms/NDP"
        settings.client_id = "ep-6a5e300b"
        settings.client_secret = "s"

        discovery_response = MagicMock()
        discovery_response.status_code = 503
        http = AsyncMock()
        http.get = AsyncMock(return_value=discovery_response)
        http.__aenter__ = AsyncMock(return_value=http)
        http.__aexit__ = AsyncMock(return_value=None)
        async_client.return_value = http

        response = client.post("/user/oidc/exchange", json=PAYLOAD)

        assert response.status_code == 502
        assert "OIDC_ISSUER" in response.json()["detail"]
