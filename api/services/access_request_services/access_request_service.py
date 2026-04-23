# api/services/access_request_services/access_request_service.py
"""
Service layer for the access-request workflow.

This module keeps the route handlers thin: it owns lifecycle rules (one
pending request per user, idempotency, etc.) and drives the AAI API when
an administrator approves a request.
"""

import logging
from typing import Any, Dict, List, Literal, Optional

from fastapi import HTTPException, status

from api.config.affinities_settings import affinities_settings
from api.config.catalog_settings import catalog_settings
from api.config.swagger_settings import swagger_settings
from api.repositories.access_request_repository import AccessRequestRepository
from api.services.auth_services import aai_client
from api.services.auth_services.authorization_service import endpoint_admin_role_name

logger = logging.getLogger(__name__)

# Module-level singleton so we reuse the MongoClient across requests.
_repository: Optional[AccessRequestRepository] = None


def require_feature_enabled() -> None:
    """Return 503 when the feature flag is off, to keep surface area clear."""
    if not swagger_settings.enable_access_requests:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Access-request workflow is disabled on this deployment.",
        )


def get_repository() -> AccessRequestRepository:
    """
    Return a cached :class:`AccessRequestRepository`, building it lazily.

    The connection string and database name are reused from
    :class:`CatalogSettings` so operators only configure MongoDB once.
    """
    global _repository
    if _repository is None:
        _repository = AccessRequestRepository(
            connection_string=catalog_settings.mongodb_connection_string,
            database_name=catalog_settings.mongodb_database,
            collection_name=swagger_settings.access_requests_collection,
        )
    return _repository


def reset_repository_for_tests() -> None:
    """Drop the cached repository so tests can inject a fresh one."""
    global _repository
    if _repository is not None:
        try:
            _repository.close()
        finally:
            _repository = None


def _require_endpoint_uuid() -> str:
    ep_uuid = (affinities_settings.ep_uuid or "").strip()
    if not ep_uuid:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Endpoint UUID is not configured; cannot grant access.",
        )
    return ep_uuid


def create_access_request(
    user_info: Dict[str, Any],
    justification: Optional[str],
) -> Dict[str, Any]:
    """
    Create a pending request for the given user.

    Raises 409 if the user already has a pending request to prevent spam
    and double-counting.
    """
    require_feature_enabled()

    user_sub = user_info.get("sub")
    username = user_info.get("username") or user_info.get("preferred_username")
    email = user_info.get("email")

    if not user_sub or not username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot identify the requesting user from their token.",
        )

    repo = get_repository()
    existing = repo.find_pending_by_user_sub(user_sub)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You already have a pending access request.",
        )

    return repo.create_pending(
        user_sub=user_sub,
        username=username,
        email=email,
        justification=justification,
    )


def list_access_requests(
    status_filter: Optional[Literal["pending", "approved", "rejected", "all"]],
) -> List[Dict[str, Any]]:
    """Return the matching requests, newest first."""
    require_feature_enabled()

    if status_filter in (None, "pending"):
        return get_repository().list(status="pending")
    if status_filter == "all":
        return get_repository().list(status=None)
    return get_repository().list(status=status_filter)


def _grant_via_aai(
    admin_token: str,
    grant_type: Literal["member", "admin"],
    username: str,
) -> None:
    """Perform the actual IDP write for an approve decision."""
    ep_uuid = _require_endpoint_uuid()

    # "member" always grants group membership. "admin" grants the admin
    # role on top — the two are complementary, not alternatives, so an
    # admin user has both.
    aai_client.add_user_to_group(admin_token, ep_uuid, username)

    if grant_type == "admin":
        admin_role = endpoint_admin_role_name()
        if admin_role:
            aai_client.assign_role(admin_token, admin_role, username)


def approve_access_request(
    request_id: str,
    admin_info: Dict[str, Any],
    admin_token: str,
    grant_type: Literal["member", "admin"],
    notes: Optional[str],
) -> Dict[str, Any]:
    """
    Approve a pending request, perform the IDP grant, and persist the decision.
    """
    require_feature_enabled()

    repo = get_repository()
    doc = repo.find_by_id(request_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Access request not found.",
        )
    if doc.get("status") != "pending":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Request is already {doc.get('status')}.",
        )

    # Execute the IDP side first. If the AAI rejects the write (admin does
    # not actually have the required role, transient outage, etc.) the
    # HTTPException propagates and the Mongo document stays pending — the
    # admin can retry without producing a phantom "approved" record.
    _grant_via_aai(admin_token, grant_type, doc["username"])

    updated = repo.mark_decided(
        request_id=request_id,
        status="approved",
        decided_by_sub=admin_info.get("sub", "unknown"),
        decided_by_username=admin_info.get("username", "unknown"),
        grant_type=grant_type,
        decision_notes=notes,
    )
    if not updated:
        # Someone else won the race between find_by_id and mark_decided.
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Request state changed before the decision was recorded.",
        )
    return updated


def reject_access_request(
    request_id: str,
    admin_info: Dict[str, Any],
    notes: Optional[str],
) -> Dict[str, Any]:
    """Mark a pending request as rejected. Does not touch the IDP."""
    require_feature_enabled()

    repo = get_repository()
    doc = repo.find_by_id(request_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Access request not found.",
        )
    if doc.get("status") != "pending":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Request is already {doc.get('status')}.",
        )

    updated = repo.mark_decided(
        request_id=request_id,
        status="rejected",
        decided_by_sub=admin_info.get("sub", "unknown"),
        decided_by_username=admin_info.get("username", "unknown"),
        grant_type=None,
        decision_notes=notes,
    )
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Request state changed before the decision was recorded.",
        )
    return updated
