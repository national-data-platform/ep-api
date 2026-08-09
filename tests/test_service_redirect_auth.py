# tests/test_service_redirect_auth.py
"""
Protecting a service behind the Endpoint's proxy.

The proxy carries no authentication of its own: whoever reaches the Endpoint
reaches the service through it. A service can now ask for callers to be
authenticated first, with a ``requires_auth`` extra — and, crucially, a
service that does not ask stays exactly as open as it was, because every
service registered before this has no such extra.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from api.routes.redirect_routes.service_redirect import (
    proxy_to_service_functional,
    proxy_to_service_with_path_functional,
    require_valid_token,
)
from api.services.service_services.redirect_service import _requires_auth


def _request(authorization=None):
    request = MagicMock()
    request.headers = {"authorization": authorization} if authorization else {}
    return request


class TestTheExtra:
    """What counts as asking for authentication."""

    def test_absent_extras_leave_the_service_open(self):
        assert _requires_auth(None) is False
        assert _requires_auth({}) is False

    def test_an_unrelated_extra_leaves_it_open(self):
        assert _requires_auth({"service_type": "API"}) is False

    @pytest.mark.parametrize("value", [True, "true", "True", "1", "yes", "on"])
    def test_the_usual_spellings_all_mean_protected(self, value):
        # Extras come back as strings from CKAN and as posted from MongoDB.
        assert _requires_auth({"requires_auth": value}) is True

    @pytest.mark.parametrize("value", [False, "false", "no", "0", "", "maybe"])
    def test_anything_else_means_open(self, value):
        assert _requires_auth({"requires_auth": value}) is False


class TestTheGate:
    """require_valid_token, on its own."""

    def test_no_token_is_refused_with_a_challenge(self):
        with pytest.raises(HTTPException) as error:
            require_valid_token(_request())

        assert error.value.status_code == 401
        assert error.value.headers["WWW-Authenticate"] == "Bearer"

    def test_a_non_bearer_authorization_is_refused(self):
        with pytest.raises(HTTPException) as error:
            require_valid_token(_request("Basic dXNlcjpwYXNz"))

        assert error.value.status_code == 401

    @patch("api.routes.redirect_routes.service_redirect.get_current_user")
    def test_a_bearer_token_is_validated_the_usual_way(self, get_user):
        get_user.return_value = {"sub": "someone"}

        require_valid_token(_request("Bearer a-token"))

        credentials = get_user.call_args[0][0]
        assert credentials.credentials == "a-token"

    @patch("api.routes.redirect_routes.service_redirect.get_current_user")
    def test_the_validators_own_failure_is_not_rewritten(self, get_user):
        # An authentication service that is down answers 502 there; turning
        # that into a 401 here would blame the caller's credentials.
        get_user.side_effect = HTTPException(status_code=502, detail="AAI down")

        with pytest.raises(HTTPException) as error:
            require_valid_token(_request("Bearer a-token"))

        assert error.value.status_code == 502


class TestTheProxy:
    """The two functional routes."""

    @pytest.mark.asyncio
    @patch("api.routes.redirect_routes.service_redirect.proxy_request")
    @patch("api.routes.redirect_routes.service_redirect.get_service_access")
    async def test_an_open_service_needs_no_token(self, access, proxy):
        access.return_value = ("https://api.example.org", False, None)
        proxy.return_value = MagicMock(status_code=200)

        result = await proxy_to_service_functional("open-service", _request())

        assert result.status_code == 200
        proxy.assert_called_once()

    @pytest.mark.asyncio
    @patch("api.routes.redirect_routes.service_redirect.proxy_request")
    @patch("api.routes.redirect_routes.service_redirect.get_service_access")
    async def test_a_protected_service_refuses_an_anonymous_caller(self, access, proxy):
        access.return_value = ("https://api.example.org", True, None)
        proxy.return_value = AsyncMock()

        with pytest.raises(HTTPException) as error:
            await proxy_to_service_functional("closed-service", _request())

        assert error.value.status_code == 401
        # The service must not be contacted at all.
        proxy.assert_not_called()

    @pytest.mark.asyncio
    @patch("api.routes.redirect_routes.service_redirect.get_current_user")
    @patch("api.routes.redirect_routes.service_redirect.proxy_request")
    @patch("api.routes.redirect_routes.service_redirect.get_service_access")
    async def test_a_protected_service_lets_an_authenticated_caller_through(
        self, access, proxy, get_user
    ):
        access.return_value = ("https://api.example.org", True, None)
        proxy.return_value = MagicMock(status_code=200)
        get_user.return_value = {"sub": "someone"}

        result = await proxy_to_service_functional(
            "closed-service", _request("Bearer a-token")
        )

        assert result.status_code == 200
        proxy.assert_called_once()

    @pytest.mark.asyncio
    @patch("api.routes.redirect_routes.service_redirect.proxy_request")
    @patch("api.routes.redirect_routes.service_redirect.get_service_access")
    async def test_subpaths_are_protected_too(self, access, proxy):
        # Otherwise the gate is a formality: /svc is closed and /svc/anything
        # reaches the same service.
        access.return_value = ("https://api.example.org", True, None)

        with pytest.raises(HTTPException) as error:
            await proxy_to_service_with_path_functional(
                "closed-service", "admin/users", _request()
            )

        assert error.value.status_code == 401
        proxy.assert_not_called()

    @pytest.mark.asyncio
    @patch("api.routes.redirect_routes.service_redirect.get_service_access")
    async def test_an_unknown_service_is_still_a_404(self, access):
        access.return_value = (None, False, "Service 'nope' not found")

        with pytest.raises(HTTPException) as error:
            await proxy_to_service_functional("nope", _request())

        assert error.value.status_code == 404
