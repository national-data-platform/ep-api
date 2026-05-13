# tests/test_user_info_route.py
"""Tests for the GET /user/info route enrichment."""

import asyncio

from api.routes.user_routes.user_info import get_user_info
from api.services.metadata_services import hash_user_id


def _call(user_info):
    return asyncio.run(get_user_info(user_info=user_info))


def test_user_info_response_is_enriched_with_ndp_user_id():
    """The enriched response carries the same hash datasets/orgs persist."""
    upstream = {
        "sub": "user-sub-abc123",
        "username": "raul",
        "email": "raul@example.com",
        "roles": ["user"],
        "groups": [],
    }

    response = _call(upstream)

    assert response["ndp_user_id"] == hash_user_id(upstream)
    # Original upstream fields are preserved unchanged.
    for key, value in upstream.items():
        assert response[key] == value


def test_user_info_response_does_not_overwrite_upstream_ndp_user_id():
    """If the upstream payload already carries ndp_user_id, we don't clobber it."""
    upstream = {
        "sub": "user-sub-abc123",
        "ndp_user_id": "upstream-override-value",
    }

    response = _call(upstream)

    assert response["ndp_user_id"] == "upstream-override-value"


def test_user_info_response_is_a_copy_not_a_mutation():
    """We must not mutate the dict the auth dependency handed us."""
    upstream = {"sub": "user-sub-abc123"}

    response = _call(upstream)

    assert "ndp_user_id" in response
    assert "ndp_user_id" not in upstream
