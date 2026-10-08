"""
Approving an access request grants access through the Endpoint's group
(issue #325).

Approval required AFFINITIES_EP_UUID, which the installer never sets, so on
every installer-made Endpoint it answered 503. It now uses the first
GROUP_NAMES entry — the group the Federation created for the Endpoint and the
one its access gate checks — and falls back to the UUID only without one.
"""

from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from api.services.access_request_services import access_request_service as service

MODULE = "api.services.access_request_services.access_request_service"


def _grant(grant_type, group_names, ep_uuid):
    aai = MagicMock()
    with (
        patch(f"{MODULE}.swagger_settings") as settings,
        patch(f"{MODULE}.affinities_settings") as affinities,
        patch(f"{MODULE}.aai_client", aai),
    ):
        settings.group_names = group_names
        affinities.ep_uuid = ep_uuid
        service._grant_via_aai("admin-token", grant_type, "alice")
    return aai


def test_a_viewer_joins_the_federation_group():
    aai = _grant("viewer", "ndp_ep/ep-123", "")

    aai.add_user_to_group.assert_called_once_with(
        "admin-token", "ndp_ep/ep-123", "alice"
    )
    aai.assign_role.assert_not_called()


def test_a_writer_gets_the_role_on_the_federation_group():
    aai = _grant("writer", "ndp_ep/ep-123", "")

    aai.assign_role.assert_called_once_with(
        "admin-token", "writer", "alice", "ndp_ep/ep-123"
    )


def test_the_first_group_name_wins_over_the_endpoint_uuid():
    aai = _grant("admin", " ndp_ep/ep-123 , other-group", "some-uuid")

    aai.add_user_to_group.assert_called_once_with(
        "admin-token", "ndp_ep/ep-123", "alice"
    )


def test_without_group_names_the_endpoint_uuid_is_used():
    aai = _grant("viewer", "", "some-uuid")

    aai.add_user_to_group.assert_called_once_with("admin-token", "some-uuid", "alice")


def test_with_neither_approval_is_refused_with_503():
    with pytest.raises(HTTPException) as refused:
        _grant("viewer", "", "")

    assert refused.value.status_code == 503
    assert "GROUP_NAMES" in refused.value.detail
