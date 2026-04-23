# api/routes/user_routes/access_requests.py
"""
REST endpoints for the access-request workflow.
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from api.models.access_request_model import (
    AccessRequest,
    AccessRequestApproveDecision,
    AccessRequestCreate,
    AccessRequestRejectDecision,
)
from api.services.access_request_services import (
    approve_access_request,
    create_access_request,
    list_access_requests,
    reject_access_request,
    require_feature_enabled,
)
from api.services.auth_services import get_current_user, require_admin

router = APIRouter()
security = HTTPBearer()


@router.post(
    "/user/access-requests",
    response_model=AccessRequest,
    status_code=status.HTTP_201_CREATED,
    summary="Submit an access request",
    description=(
        "Authenticated user asks to be granted access to this Endpoint. "
        "Only one pending request per user is allowed."
    ),
    responses={
        201: {"description": "Access request created"},
        400: {"description": "Cannot identify the user from their token"},
        409: {"description": "The user already has a pending request"},
        503: {"description": "Access-request workflow is disabled"},
    },
)
async def create_request(
    payload: AccessRequestCreate,
    user_info: Dict[str, Any] = Depends(get_current_user),
) -> AccessRequest:
    require_feature_enabled()
    doc = create_access_request(user_info, payload.justification)
    return AccessRequest.from_document(doc)


@router.get(
    "/user/access-requests",
    response_model=List[AccessRequest],
    summary="List access requests (admin only)",
    description=(
        "Return pending access requests by default. Use `status=all` to "
        "include approved and rejected, or pass a specific status."
    ),
    responses={
        200: {"description": "Access requests returned"},
        403: {"description": "Administrator role required"},
        503: {"description": "Access-request workflow is disabled"},
    },
)
async def list_requests(
    status_filter: Optional[str] = Query(
        None,
        alias="status",
        pattern="^(pending|approved|rejected|all)$",
    ),
    _admin: Dict[str, Any] = Depends(require_admin),
) -> List[AccessRequest]:
    require_feature_enabled()
    docs = list_access_requests(status_filter)  # type: ignore[arg-type]
    return [AccessRequest.from_document(doc) for doc in docs]


@router.post(
    "/user/access-requests/{request_id}/approve",
    response_model=AccessRequest,
    summary="Approve an access request (admin only)",
    description=(
        "Approve a pending access request. The administrator chooses what to "
        "grant via `grant_type`: `member` adds the user to the endpoint "
        "group, `admin` also assigns the endpoint admin role.\n\n"
        "The IDP write is performed using the administrator's own bearer "
        "token, so no service account is involved."
    ),
    responses={
        200: {"description": "Request approved"},
        403: {"description": "Administrator role required"},
        404: {"description": "Request not found"},
        409: {"description": "Request is not pending"},
        502: {"description": "IDP rejected or could not perform the grant"},
        503: {"description": "Access-request workflow is disabled"},
    },
)
async def approve_request(
    request_id: str,
    decision: AccessRequestApproveDecision,
    request: Request,
    admin_info: Dict[str, Any] = Depends(require_admin),
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> AccessRequest:
    require_feature_enabled()
    # `request` kept in the signature so an Authorization-less caller would
    # hit the HTTPBearer dependency before reaching this body.
    _ = request
    doc = approve_access_request(
        request_id=request_id,
        admin_info=admin_info,
        admin_token=credentials.credentials,
        grant_type=decision.grant_type,
        notes=decision.notes,
    )
    return AccessRequest.from_document(doc)


@router.post(
    "/user/access-requests/{request_id}/reject",
    response_model=AccessRequest,
    summary="Reject an access request (admin only)",
    description="Reject a pending access request. The IDP is not touched.",
    responses={
        200: {"description": "Request rejected"},
        403: {"description": "Administrator role required"},
        404: {"description": "Request not found"},
        409: {"description": "Request is not pending"},
        503: {"description": "Access-request workflow is disabled"},
    },
)
async def reject_request(
    request_id: str,
    decision: AccessRequestRejectDecision,
    admin_info: Dict[str, Any] = Depends(require_admin),
) -> AccessRequest:
    require_feature_enabled()
    doc = reject_access_request(
        request_id=request_id,
        admin_info=admin_info,
        notes=decision.notes,
    )
    return AccessRequest.from_document(doc)
