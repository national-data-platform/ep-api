# tests/test_user_login_route.py
"""
Tests for the POST /user/login route.
"""

from unittest.mock import patch

from fastapi import HTTPException, status
from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)


class TestUserLoginRoute:
    """Tests for the /user/login endpoint."""

    @patch("api.routes.user_routes.user_login.authenticate_with_credentials")
    def test_login_success_returns_idp_payload(self, mock_auth):
        """A successful login returns the IDP payload with the access token."""
        mock_auth.return_value = {
            "access_token": "tok.en.value",
            "token_type": "Bearer",
            "roles": ["user"],
            "groups": [],
        }

        response = client.post(
            "/user/login",
            json={"username": "john.doe", "password": "s3cret"},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["access_token"] == "tok.en.value"
        assert body["token_type"] == "Bearer"
        mock_auth.assert_called_once_with("john.doe", "s3cret")

    @patch("api.routes.user_routes.user_login.authenticate_with_credentials")
    def test_login_invalid_credentials_returns_401(self, mock_auth):
        """Invalid credentials surface as a 401 response."""
        mock_auth.side_effect = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

        response = client.post(
            "/user/login",
            json={"username": "john.doe", "password": "wrong"},
        )

        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid username or password"

    @patch("api.routes.user_routes.user_login.authenticate_with_credentials")
    def test_login_idp_unavailable_returns_502(self, mock_auth):
        """IDP connectivity errors surface as a 502 response."""
        mock_auth.side_effect = HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Authentication service is unavailable.",
        )

        response = client.post(
            "/user/login",
            json={"username": "john.doe", "password": "s3cret"},
        )

        assert response.status_code == 502

    def test_login_missing_username_returns_422(self):
        """Omitting username triggers a validation error."""
        response = client.post(
            "/user/login",
            json={"password": "s3cret"},
        )

        assert response.status_code == 422

    def test_login_missing_password_returns_422(self):
        """Omitting password triggers a validation error."""
        response = client.post(
            "/user/login",
            json={"username": "john.doe"},
        )

        assert response.status_code == 422

    def test_login_empty_username_returns_422(self):
        """An empty username is rejected by the payload validator."""
        response = client.post(
            "/user/login",
            json={"username": "", "password": "s3cret"},
        )

        assert response.status_code == 422

    def test_login_empty_password_returns_422(self):
        """An empty password is rejected by the payload validator."""
        response = client.post(
            "/user/login",
            json={"username": "john.doe", "password": ""},
        )

        assert response.status_code == 422

    def test_login_does_not_require_authentication(self):
        """The login endpoint is reachable without an Authorization header."""
        with patch(
            "api.routes.user_routes.user_login.authenticate_with_credentials"
        ) as mock_auth:
            mock_auth.return_value = {
                "access_token": "tok",
                "token_type": "Bearer",
            }

            response = client.post(
                "/user/login",
                json={"username": "john.doe", "password": "s3cret"},
            )

            assert response.status_code == 200
