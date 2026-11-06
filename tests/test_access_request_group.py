"""
Approving an access request grants access through the Endpoint's group, the
one the Federation created with its client: ndp_ep/<AUTHZ_CLIENT_ID>, whose
levels the client's permission gates are decided on (issue #325).
"""

from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from api.config.swagger_settings import swagger_settings
from api.services.access_request_services import access_request_service as service

MODULE = "api.services.access_request_services.access_request_service"


def _grant(grant_type, client_id):
    aai = MagicMock()
    with (
        patch.object(swagger_settings, "authz_client_id", client_id),
        patch(f"{MODULE}.aai_client", aai),
    ):
        service._grant_via_aai("admin-token", grant_type, "alice")
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
    aai = _grant(grant_type, "ep-123")

    aai.add_user_to_group.assert_called_once_with(
        "admin-token", "ndp_ep/ep-123", "alice", level
    )


def test_without_a_client_approval_is_refused_with_503():
    with pytest.raises(HTTPException) as refused:
        _grant("viewer", "")

    assert refused.value.status_code == 503
    assert "AUTHZ_CLIENT_ID" in refused.value.detail
