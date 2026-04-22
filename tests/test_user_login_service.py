# tests/test_user_login_service.py
"""
Tests for the user_login authentication service.
"""

from unittest.mock import MagicMock, patch

import pytest
import requests
from fastapi import HTTPException

from api.services.auth_services.user_login import (
    _build_login_url,
    authenticate_with_credentials,
)


class TestBuildLoginUrl:
    """Test cases for _build_login_url."""

    @patch("api.services.auth_services.user_login.swagger_settings")
    def test_builds_login_url_from_information_endpoint(self, mock_settings):
        """Login URL is derived from the configured auth_api_url base."""
        mock_settings.auth_api_url = "https://idp.example.com/information"

        result = _build_login_url()

        assert result == "https://idp.example.com/user/login"

    @patch("api.services.auth_services.user_login.swagger_settings")
    def test_builds_login_url_preserves_port(self, mock_settings):
        """Login URL preserves scheme, host and port from the configured URL."""
        mock_settings.auth_api_url = "http://10.0.0.1:5055/information"

        result = _build_login_url()

        assert result == "http://10.0.0.1:5055/user/login"

    @patch("api.services.auth_services.user_login.swagger_settings")
    def test_empty_auth_api_url_raises_502(self, mock_settings):
        """An unconfigured auth_api_url raises a 502 HTTPException."""
        mock_settings.auth_api_url = ""

        with pytest.raises(HTTPException) as exc_info:
            _build_login_url()

        assert exc_info.value.status_code == 502

    @patch("api.services.auth_services.user_login.swagger_settings")
    def test_missing_scheme_raises_502(self, mock_settings):
        """An auth_api_url without scheme raises a 502 HTTPException."""
        mock_settings.auth_api_url = "idp.example.com/information"

        with pytest.raises(HTTPException) as exc_info:
            _build_login_url()

        assert exc_info.value.status_code == 502


class TestAuthenticateWithCredentials:
    """Test cases for authenticate_with_credentials."""

    @patch("api.services.auth_services.user_login.requests.post")
    @patch("api.services.auth_services.user_login.swagger_settings")
    def test_successful_login_returns_idp_payload(self, mock_settings, mock_post):
        """A 200 response with access_token is forwarded to the caller."""
        mock_settings.auth_api_url = "https://idp.example.com/information"

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "abc.def.ghi",
            "token_type": "Bearer",
            "roles": ["user"],
            "groups": [],
        }
        mock_post.return_value = mock_response

        result = authenticate_with_credentials("john", "s3cret")

        assert result["access_token"] == "abc.def.ghi"
        assert result["token_type"] == "Bearer"
        mock_post.assert_called_once_with(
            "https://idp.example.com/user/login",
            json={"username": "john", "password": "s3cret"},
            timeout=10,
        )

    @patch("api.services.auth_services.user_login.requests.post")
    @patch("api.services.auth_services.user_login.swagger_settings")
    def test_invalid_credentials_raises_401(self, mock_settings, mock_post):
        """A 401 response from the IDP is surfaced as a 401 HTTPException."""
        mock_settings.auth_api_url = "https://idp.example.com/information"

        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.json.return_value = {"error": "Invalid username or password"}
        mock_post.return_value = mock_response

        with pytest.raises(HTTPException) as exc_info:
            authenticate_with_credentials("john", "wrong")

        assert exc_info.value.status_code == 401
        assert "Invalid username or password" in exc_info.value.detail

    @patch("api.services.auth_services.user_login.requests.post")
    @patch("api.services.auth_services.user_login.swagger_settings")
    def test_bad_request_response_is_401(self, mock_settings, mock_post):
        """A 400 from the IDP is treated as an authentication failure."""
        mock_settings.auth_api_url = "https://idp.example.com/information"

        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json.return_value = {
            "error": "username and password are required"
        }
        mock_post.return_value = mock_response

        with pytest.raises(HTTPException) as exc_info:
            authenticate_with_credentials("", "")

        assert exc_info.value.status_code == 401
        assert "username and password are required" in exc_info.value.detail

    @patch("api.services.auth_services.user_login.requests.post")
    @patch("api.services.auth_services.user_login.swagger_settings")
    def test_forbidden_response_is_401(self, mock_settings, mock_post):
        """A 403 from the IDP is treated as an authentication failure."""
        mock_settings.auth_api_url = "https://idp.example.com/information"

        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.json.return_value = {"error": "account locked"}
        mock_post.return_value = mock_response

        with pytest.raises(HTTPException) as exc_info:
            authenticate_with_credentials("john", "s3cret")

        assert exc_info.value.status_code == 401
        assert "account locked" in exc_info.value.detail

    @patch("api.services.auth_services.user_login.requests.post")
    @patch("api.services.auth_services.user_login.swagger_settings")
    def test_network_error_raises_502(self, mock_settings, mock_post):
        """Network errors talking to the IDP surface as 502."""
        mock_settings.auth_api_url = "https://idp.example.com/information"
        mock_post.side_effect = requests.exceptions.ConnectionError("boom")

        with pytest.raises(HTTPException) as exc_info:
            authenticate_with_credentials("john", "s3cret")

        assert exc_info.value.status_code == 502
        assert "unavailable" in exc_info.value.detail.lower()

    @patch("api.services.auth_services.user_login.requests.post")
    @patch("api.services.auth_services.user_login.swagger_settings")
    def test_unexpected_status_raises_502(self, mock_settings, mock_post):
        """Unexpected IDP status codes surface as 502."""
        mock_settings.auth_api_url = "https://idp.example.com/information"

        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "internal error"
        mock_post.return_value = mock_response

        with pytest.raises(HTTPException) as exc_info:
            authenticate_with_credentials("john", "s3cret")

        assert exc_info.value.status_code == 502

    @patch("api.services.auth_services.user_login.requests.post")
    @patch("api.services.auth_services.user_login.swagger_settings")
    def test_missing_access_token_raises_502(self, mock_settings, mock_post):
        """A 200 response without access_token is considered a bad gateway."""
        mock_settings.auth_api_url = "https://idp.example.com/information"

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"roles": ["user"]}
        mock_post.return_value = mock_response

        with pytest.raises(HTTPException) as exc_info:
            authenticate_with_credentials("john", "s3cret")

        assert exc_info.value.status_code == 502
        assert "access token" in exc_info.value.detail.lower()

    @patch("api.services.auth_services.user_login.requests.post")
    @patch("api.services.auth_services.user_login.swagger_settings")
    def test_non_json_success_response_raises_502(self, mock_settings, mock_post):
        """A 200 response with a non-JSON body surfaces as 502."""
        mock_settings.auth_api_url = "https://idp.example.com/information"

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.side_effect = ValueError("not json")
        mock_post.return_value = mock_response

        with pytest.raises(HTTPException) as exc_info:
            authenticate_with_credentials("john", "s3cret")

        assert exc_info.value.status_code == 502

    @patch("api.services.auth_services.user_login.requests.post")
    @patch("api.services.auth_services.user_login.swagger_settings")
    def test_auth_error_without_json_body_uses_default_message(
        self, mock_settings, mock_post
    ):
        """A 401 whose body is not JSON still surfaces as 401 with a default."""
        mock_settings.auth_api_url = "https://idp.example.com/information"

        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.json.side_effect = ValueError("not json")
        mock_post.return_value = mock_response

        with pytest.raises(HTTPException) as exc_info:
            authenticate_with_credentials("john", "s3cret")

        assert exc_info.value.status_code == 401
        assert exc_info.value.detail == "Invalid username or password"
