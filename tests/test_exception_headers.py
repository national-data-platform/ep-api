"""
Headers set on an HTTPException reach the client (issue #387).

``http_exception_handler`` rebuilt every error as a new JSONResponse from the
status and detail only, so headers such as ``WWW-Authenticate: Bearer``, which
``get_current_user`` sets on every 401, never left the Endpoint.
"""

from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from api.exceptions.handlers import http_exception_handler
from api.main import app


@pytest.mark.asyncio
async def test_handler_keeps_the_exception_headers():
    request = MagicMock()
    request.url.path = "/user/info"
    exc = HTTPException(
        status_code=401,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )

    response = await http_exception_handler(request, exc)

    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"


@pytest.mark.asyncio
async def test_handler_without_headers_still_works():
    request = MagicMock()
    request.url.path = "/missing"

    response = await http_exception_handler(
        request, HTTPException(status_code=404, detail="Not found")
    )

    assert response.status_code == 404
    assert "WWW-Authenticate" not in response.headers


def test_a_rejected_token_answers_401_with_www_authenticate():
    rejected = MagicMock()
    rejected.status_code = 401
    with (
        patch(
            "api.services.auth_services.get_current_user.swagger_settings"
        ) as settings,
        patch(
            "api.services.auth_services.get_current_user.requests.post",
            return_value=rejected,
        ),
    ):
        settings.test_token = ""
        settings.auth_api_url = "https://aai.example.org/information"
        response = TestClient(app).get(
            "/user/info", headers={"Authorization": "Bearer not-a-valid-token"}
        )

    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"
    assert response.json()["error"] == "Unauthorized"
