"""
Auth-service failures must not be reported as invalid tokens (issue #195).

get_current_user validates against an external service. A 401 from that
service is a bad token; anything else (unreachable, 500, unexpected status,
malformed body) is an infrastructure problem and must not be flattened into
401 "Authentication failed".
"""

from unittest.mock import MagicMock, patch

import pytest
import requests
from fastapi import HTTPException, status

from api.services.auth_services.get_current_user import get_current_user


class _Creds:
    def __init__(self, token):
        self.credentials = token


def _call(token="a-token"):
    with patch(
        "api.services.auth_services.get_current_user.swagger_settings"
    ) as settings:
        settings.test_token = "the-test-token"
        settings.auth_api_url = "https://aai.example.org/information"
        return get_current_user(token_data=_Creds(token))


def _resp(status_code, json_body=None):
    r = MagicMock()
    r.status_code = status_code
    r.json.return_value = json_body if json_body is not None else {}
    r.text = str(json_body)
    return r


def test_auth_service_500_is_502_not_401():
    with patch(
        "api.services.auth_services.get_current_user.requests.post",
        return_value=_resp(500),
    ):
        with pytest.raises(HTTPException) as exc:
            _call()
    assert exc.value.status_code == status.HTTP_502_BAD_GATEWAY


def test_auth_service_unexpected_status_is_502_not_401():
    with patch(
        "api.services.auth_services.get_current_user.requests.post",
        return_value=_resp(418),
    ):
        with pytest.raises(HTTPException) as exc:
            _call()
    assert exc.value.status_code == status.HTTP_502_BAD_GATEWAY


def test_auth_service_unreachable_is_502_not_401():
    with patch(
        "api.services.auth_services.get_current_user.requests.post",
        side_effect=requests.exceptions.ConnectionError("no route"),
    ):
        with pytest.raises(HTTPException) as exc:
            _call()
    assert exc.value.status_code == status.HTTP_502_BAD_GATEWAY


def test_invalid_token_is_still_401():
    with patch(
        "api.services.auth_services.get_current_user.requests.post",
        return_value=_resp(401),
    ):
        with pytest.raises(HTTPException) as exc:
            _call()
    assert exc.value.status_code == status.HTTP_401_UNAUTHORIZED


def test_error_in_body_is_401():
    with patch(
        "api.services.auth_services.get_current_user.requests.post",
        return_value=_resp(200, {"error": "token expired"}),
    ):
        with pytest.raises(HTTPException) as exc:
            _call()
    assert exc.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert "token expired" in exc.value.detail


def test_valid_token_returns_user_info():
    with patch(
        "api.services.auth_services.get_current_user.requests.post",
        return_value=_resp(200, {"roles": ["ndp_admin"], "sub": "abc"}),
    ):
        info = _call()
    assert info["sub"] == "abc"
