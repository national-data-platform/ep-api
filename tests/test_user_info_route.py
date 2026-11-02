# tests/test_user_info_route.py
"""Tests for GET /user/info: the enrichment, effective_role and the entry check."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from api.config.swagger_settings import swagger_settings
from api.routes.user_routes.user_info import get_user_info
from api.services.metadata_services import hash_user_id

TOKEN = MagicMock(credentials="user-token")


def test_user_info_response_is_enriched_with_ndp_user_id(keycloak):
    """The enriched response carries the same hash datasets/orgs persist."""
    keycloak.grant("viewer")
    upstream = {
        "sub": "user-sub-abc123",
        "username": "raul",
        "email": "raul@example.com",
        "roles": ["user"],
        "groups": [],
    }

    response = get_user_info(upstream, TOKEN)

    assert response["ndp_user_id"] == hash_user_id(upstream)
    # Original upstream fields are preserved unchanged.
    for key, value in upstream.items():
        assert response[key] == value


def test_user_info_response_does_not_overwrite_upstream_fields(keycloak):
    """Upstream ndp_user_id or effective_role values are not clobbered."""
    keycloak.grant("viewer")
    upstream = {"sub": "u1", "ndp_user_id": "upstream", "effective_role": "set"}

    response = get_user_info(upstream, TOKEN)

    assert response["ndp_user_id"] == "upstream"
    assert response["effective_role"] == "set"


def test_user_info_response_is_a_copy_not_a_mutation(keycloak):
    """We must not mutate the dict the auth dependency handed us."""
    keycloak.grant("viewer")
    upstream = {"sub": "user-sub-abc123"}

    response = get_user_info(upstream, TOKEN)

    assert "ndp_user_id" in response
    assert "ndp_user_id" not in upstream
    assert "effective_role" not in upstream


@pytest.mark.parametrize(
    "level,expected",
    [("admin", "admin"), ("editor", "writer"), ("viewer", "viewer")],
)
def test_effective_role_is_the_highest_gate_passed(keycloak, level, expected):
    keycloak.grant(level)

    response = get_user_info({"sub": "u1", "roles": ["ndp_admin"]}, TOKEN)

    assert response["effective_role"] == expected


def test_effective_role_stops_at_the_first_gate_that_passes(keycloak):
    keycloak.grant("admin")

    get_user_info({"sub": "u1"}, TOKEN)

    assert keycloak.asked == [("user-token", "admin-area")]


def test_a_token_keycloak_rejects_is_401_not_none(keycloak):
    with patch(
        "api.services.auth_services.ep_access_gate.requests.post",
        return_value=MagicMock(status_code=401),
    ):
        with pytest.raises(HTTPException) as exc_info:
            get_user_info({"sub": "u1"}, TOKEN)
    assert exc_info.value.status_code == 401


@pytest.mark.parametrize(
    "client,level,allowed",
    [("", None, True), ("ep-test", "viewer", True), ("ep-test", None, False)],
)
def test_entry_check(keycloak, client, level, allowed):
    """Only an Endpoint with a client turns away callers without a level."""
    keycloak.grant(level)
    with patch.object(swagger_settings, "authz_client_id", client):
        if allowed:
            assert get_user_info({"sub": "u1"}, TOKEN)["sub"] == "u1"
        else:
            with pytest.raises(HTTPException) as exc_info:
                get_user_info({"sub": "u1"}, TOKEN)
            assert exc_info.value.status_code == 403
            assert "permission to access this Endpoint" in exc_info.value.detail


def test_the_route_through_fastapi(keycloak):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from api.routes.user_routes.user_info import router
    from api.services.auth_services import get_current_user

    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_current_user] = lambda: {"sub": "u1"}
    keycloak.grant("viewer")

    response = TestClient(app).get(
        "/user/info", headers={"Authorization": "Bearer user-token"}
    )

    assert response.status_code == 200
    assert response.json()["effective_role"] == "viewer"
