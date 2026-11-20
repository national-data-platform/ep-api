# tests/test_oidc_code_exchange.py
"""
Signing in on the identity provider's page with the Endpoint's own
confidential client: POST /user/oidc/token redeems the code with the
client's secret, for OIDC_REDIRECT_URI only.
"""

from unittest.mock import MagicMock, patch

import pytest
import requests
from fastapi import HTTPException
from fastapi.testclient import TestClient
from pydantic import SecretStr

from api.config.swagger_settings import Settings
from api.main import app
from api.services.auth_services.user_login import exchange_authorization_code

VERIFIER = "v" * 43
REDIRECT = "https://ep.example.org/ep-api/ui/auth/callback"


@pytest.fixture
def settings():
    with patch(
        "api.services.auth_services.user_login.swagger_settings"
    ) as mock_settings:
        mock_settings.oidc_enabled = True
        mock_settings.oidc_service_client_id = "ep-0123"
        mock_settings.oidc_service_client_secret = SecretStr("s3cret")
        mock_settings.oidc_redirect_uri = REDIRECT
        mock_settings.keycloak_token_url = (
            "https://idp.example.org/realms/NDP/protocol/openid-connect/token"
        )
        yield mock_settings


def _answer(status_code, payload):
    response = MagicMock()
    response.status_code = status_code
    response.json.return_value = payload
    return response


@patch("api.services.auth_services.user_login.requests.post")
def test_redeems_the_code_with_the_secret_for_the_configured_redirect(
    mock_post, settings
):
    mock_post.return_value = _answer(
        200,
        {
            "access_token": "the-token",
            "refresh_token": "the-refresh",
            "id_token": "the-id",
            "token_type": "Bearer",
            "expires_in": 300,
        },
    )

    result = exchange_authorization_code("the-code", VERIFIER)

    assert result == {
        "access_token": "the-token",
        "token_type": "Bearer",
        "expires_in": 300,
    }
    mock_post.assert_called_once_with(
        "https://idp.example.org/realms/NDP/protocol/openid-connect/token",
        data={
            "grant_type": "authorization_code",
            "code": "the-code",
            "code_verifier": VERIFIER,
            "redirect_uri": REDIRECT,
            "client_id": "ep-0123",
            "client_secret": "s3cret",
        },
        timeout=10,
    )


@patch("api.services.auth_services.user_login.requests.post")
def test_without_pkce_no_verifier_is_sent(mock_post, settings):
    mock_post.return_value = _answer(200, {"access_token": "the-token"})

    exchange_authorization_code("the-code")

    assert "code_verifier" not in mock_post.call_args.kwargs["data"]
    assert mock_post.call_args.kwargs["data"]["redirect_uri"] == REDIRECT


@pytest.mark.parametrize(
    "missing",
    [
        ("oidc_enabled", False),
        ("oidc_service_client_id", ""),
        ("oidc_service_client_secret", SecretStr("")),
        ("oidc_redirect_uri", ""),
    ],
)
@patch("api.services.auth_services.user_login.requests.post")
def test_not_set_up_is_503_and_asks_nothing(mock_post, settings, missing):
    setattr(settings, *missing)

    with pytest.raises(HTTPException) as exc:
        exchange_authorization_code("the-code", VERIFIER)

    assert exc.value.status_code == 503
    mock_post.assert_not_called()


@patch("api.services.auth_services.user_login.requests.post")
def test_a_refused_code_is_400_with_the_reason(mock_post, settings):
    mock_post.return_value = _answer(
        400, {"error": "invalid_grant", "error_description": "Code not valid"}
    )

    with pytest.raises(HTTPException) as exc:
        exchange_authorization_code("the-code", VERIFIER)

    assert exc.value.status_code == 400
    assert "Code not valid" in exc.value.detail


@pytest.mark.parametrize("error", ["invalid_client", "unauthorized_client"])
@patch("api.services.auth_services.user_login.requests.post")
def test_a_refused_client_is_a_configuration_error(mock_post, settings, error):
    mock_post.return_value = _answer(401, {"error": error})

    with pytest.raises(HTTPException) as exc:
        exchange_authorization_code("the-code", VERIFIER)

    assert exc.value.status_code == 503
    assert "OIDC_SERVICE_CLIENT_SECRET" in exc.value.detail
    assert "s3cret" not in exc.value.detail


@patch("api.services.auth_services.user_login.requests.post")
def test_unreachable_is_502(mock_post, settings):
    mock_post.side_effect = requests.exceptions.ConnectionError("boom")

    with pytest.raises(HTTPException) as exc:
        exchange_authorization_code("the-code", VERIFIER)

    assert exc.value.status_code == 502


@patch("api.services.auth_services.user_login.requests.post")
def test_an_answer_without_a_token_is_502(mock_post, settings):
    mock_post.return_value = _answer(500, None)
    mock_post.return_value.json.side_effect = ValueError("not json")

    with pytest.raises(HTTPException) as exc:
        exchange_authorization_code("the-code", VERIFIER)

    assert exc.value.status_code == 502


class TestRoute:
    client = TestClient(app)

    @patch("api.routes.user_routes.user_login.exchange_authorization_code")
    def test_hands_the_code_and_verifier_over(self, mock_exchange):
        mock_exchange.return_value = {"access_token": "the-token"}

        response = self.client.post(
            "/user/oidc/token", json={"code": "the-code", "code_verifier": VERIFIER}
        )

        assert response.status_code == 200
        assert response.json() == {"access_token": "the-token"}
        mock_exchange.assert_called_once_with("the-code", VERIFIER)

    @patch("api.routes.user_routes.user_login.exchange_authorization_code")
    def test_the_verifier_is_optional(self, mock_exchange):
        mock_exchange.return_value = {"access_token": "the-token"}

        response = self.client.post("/user/oidc/token", json={"code": "the-code"})

        assert response.status_code == 200
        mock_exchange.assert_called_once_with("the-code", None)

    @pytest.mark.parametrize(
        "body",
        [
            {},
            {"code": "", "code_verifier": VERIFIER},
            {"code": "the-code", "code_verifier": "short"},
        ],
    )
    @patch("api.routes.user_routes.user_login.exchange_authorization_code")
    def test_an_incomplete_request_is_422(self, mock_exchange, body):
        response = self.client.post("/user/oidc/token", json=body)

        assert response.status_code == 422
        mock_exchange.assert_not_called()

    @patch("api.routes.user_routes.user_login.exchange_authorization_code")
    def test_a_refusal_is_passed_on(self, mock_exchange):
        mock_exchange.side_effect = HTTPException(status_code=503, detail="not set up")

        response = self.client.post(
            "/user/oidc/token", json={"code": "the-code", "code_verifier": VERIFIER}
        )

        assert response.status_code == 503


def test_signs_in_to_the_realm_on_keycloak_url(monkeypatch):
    monkeypatch.setenv("KEYCLOAK_URL", "https://idp.example.org/temp/information")
    monkeypatch.setenv("AUTHZ_REALM", "NDP")
    monkeypatch.setenv("OIDC_ISSUER", "https://other.example.org/realms/X")
    monkeypatch.setenv("OIDC_ENABLED", "True")
    monkeypatch.setenv("OIDC_REDIRECT_URI", REDIRECT)
    monkeypatch.setenv("OIDC_SERVICE_CLIENT_ID", "ep-0123")
    monkeypatch.setenv("OIDC_SERVICE_CLIENT_SECRET", "s3cret")

    with (
        patch(
            "api.services.auth_services.user_login.swagger_settings",
            Settings(_env_file=None),
        ),
        patch("api.services.auth_services.user_login.requests.post") as mock_post,
    ):
        mock_post.return_value = _answer(200, {"access_token": "the-token"})
        exchange_authorization_code("the-code")

    assert mock_post.call_args.args[0] == (
        "https://idp.example.org/realms/NDP/protocol/openid-connect/token"
    )
