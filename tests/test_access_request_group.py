"""
Approving an access request grants access through the Endpoint's group, the
one the Federation created with its client: ndp_ep/<OIDC_SERVICE_CLIENT_ID>,
whose levels the client's permission gates are decided on (issue #325).

The AAI changes a group under ndp_ep only when the calling app proves it is
that group's own client, with a client-credentials token in
X-Client-Assertion; the Endpoint gets one with the same client's secret
(OIDC_SERVICE_CLIENT_SECRET).
"""

from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException
from pydantic import SecretStr

from api.config.swagger_settings import swagger_settings
from api.services.access_request_services import access_request_service as service

MODULE = "api.services.access_request_services.access_request_service"


def _grant(grant_type, client_id, secret=""):
    aai = MagicMock()
    aai.client_login.return_value = "client-tok"
    with (
        patch.object(swagger_settings, "oidc_service_client_id", client_id),
        patch.object(swagger_settings, "oidc_service_client_secret", SecretStr(secret)),
        patch(f"{MODULE}.aai_client", aai),
    ):
        service._grant_via_aai("admin-token", grant_type, "alice-uuid")
    return aai


@pytest.mark.parametrize(
    "grant_type,level",
    [
        ("viewer", "viewer"),
        ("member", "viewer"),
        ("writer", "editor"),
        ("admin", "admin"),
    ],
)
def test_each_tier_joins_the_endpoint_group_at_its_level(grant_type, level):
    """The identity provider calls the write tier "editor"."""
    aai = _grant(grant_type, "ep-123", "s3cret")

    aai.add_user_to_group.assert_called_once_with(
        "admin-token",
        "ndp_ep/ep-123",
        "alice-uuid",
        level,
        client_assertion="client-tok",
    )


def test_the_endpoint_client_vouches_for_the_call():
    """The assertion is the group's own client, as the AAI requires."""
    aai = _grant("viewer", "ep-123", "s3cret")

    aai.client_login.assert_called_once_with("ep-123", "s3cret")


def test_without_a_secret_approval_is_refused_with_503():
    """The AAI refuses a write to an ndp_ep group without the Endpoint's
    assertion, so say which setting is missing instead of asking it."""
    aai = MagicMock()
    with (
        patch.object(swagger_settings, "oidc_service_client_id", "ep-123"),
        patch.object(swagger_settings, "oidc_service_client_secret", SecretStr("")),
        patch(f"{MODULE}.aai_client", aai),
        pytest.raises(HTTPException) as refused,
    ):
        service._grant_via_aai("admin-token", "viewer", "alice-uuid")

    assert refused.value.status_code == 503
    assert "OIDC_SERVICE_CLIENT_SECRET" in refused.value.detail
    aai.client_login.assert_not_called()
    aai.add_user_to_group.assert_not_called()


def test_without_a_client_approval_is_refused_with_503():
    with pytest.raises(HTTPException) as refused:
        _grant("viewer", "", "s3cret")

    assert refused.value.status_code == 503
    assert "OIDC_SERVICE_CLIENT_ID" in refused.value.detail


def test_a_refused_client_stops_the_grant():
    aai = MagicMock()
    aai.client_login.side_effect = HTTPException(status_code=503, detail="refused")
    with (
        patch.object(swagger_settings, "oidc_service_client_id", "ep-123"),
        patch.object(swagger_settings, "oidc_service_client_secret", SecretStr("bad")),
        patch(f"{MODULE}.aai_client", aai),
        pytest.raises(HTTPException) as refused,
    ):
        service._grant_via_aai("admin-token", "viewer", "alice-uuid")

    assert refused.value.status_code == 503
    aai.add_user_to_group.assert_not_called()
