# api/routes/user_routes/user_info.py

from typing import Any, Dict

from fastapi import APIRouter, Depends

from api.services.auth_services import effective_role, get_user_for_endpoint_access
from api.services.metadata_services import hash_user_id

router = APIRouter()


@router.get(
    "/user/info",
    response_model=Dict[str, Any],
    summary="Get current user information",
    description=(
        "Retrieve detailed information about the currently authenticated user.\n\n"
        "This endpoint returns the user profile data from the authentication "
        "service, including roles, groups, username, and other available "
        "user attributes.\n\n"
        "### Authentication Required\n"
        "This endpoint requires a valid Bearer token in the Authorization "
        "header.\n\n"
        "### Response Format\n"
        "The response format depends on the authentication service but "
        "typically includes:\n"
        "- **roles**: List of user roles\n"
        "- **groups**: List of groups the user belongs to\n"
        "- **sub**: User identifier\n"
        "- **username**: Username\n"
        "- **email**: User email (if available)\n\n"
        "### Example Response\n"
        "```json\n"
        "{\n"
        '  "roles": ["admin", "user"],\n'
        '  "groups": ["University Research Group", "researchers"],\n'
        '  "sub": "user123",\n'
        '  "username": "john.doe",\n'
        '  "email": "john.doe@university.edu"\n'
        "}\n"
        "```\n"
    ),
    responses={
        200: {
            "description": "User information retrieved successfully",
            "content": {
                "application/json": {
                    "example": {
                        "roles": ["admin", "user"],
                        "groups": ["University Research Group", "researchers"],
                        "sub": "user123",
                        "username": "john.doe",
                        "email": "john.doe@university.edu",
                    }
                }
            },
        },
        401: {
            "description": "Unauthorized - Invalid or missing token",
            "content": {
                "application/json": {"example": {"detail": "Invalid or expired token"}}
            },
        },
        403: {
            "description": "Forbidden - Token does not have sufficient permissions",
            "content": {
                "application/json": {
                    "example": {"detail": "Token does not have sufficient permissions"}
                }
            },
        },
        502: {
            "description": "Bad Gateway - Authentication service unavailable",
            "content": {
                "application/json": {
                    "example": {"detail": "Authentication service is unavailable"}
                }
            },
        },
    },
)
async def get_user_info(
    user_info: Dict[str, Any] = Depends(get_user_for_endpoint_access),
) -> Dict[str, Any]:
    """
    Get current user information from the authentication service.

    This endpoint acts as a passthrough to the authentication service,
    returning the complete user profile information that was retrieved
    during token validation. It also doubles as the UI's entry gate:
    when ``ENABLE_GROUP_BASED_ACCESS`` is enabled, users that do not
    satisfy any of the configured authorization paths are rejected
    with a 403 response.

    On top of the upstream payload, the response is enriched with the
    user's own ``ndp_user_id`` — the same SHA-256-based hash that the EP
    persists alongside resources created by this user. The hash is
    derived from the ``sub`` claim and is *not* PII; surfacing it here
    lets clients (notably the Search UI) filter resources by the
    "creator hash" they already see in resource extras without having
    to compute the hash themselves.

    Parameters
    ----------
    user_info : Dict[str, Any]
        User information provided by the endpoint-access dependency.

    Returns
    -------
    Dict[str, Any]
        Complete user information as returned by the authentication
        service, plus a top-level ``ndp_user_id`` field.

    Raises
    ------
    HTTPException
        401: If token is invalid or expired
        403: If the user is not authorized to access this Endpoint
        502: If authentication service is unavailable
    """
    # Additive enrichment — never overwrite an upstream value that
    # happens to share the name, to keep this strictly backwards
    # compatible if the auth service ever starts returning it itself.
    enriched = dict(user_info)
    enriched.setdefault("ndp_user_id", hash_user_id(user_info))
    # effective_role lets the UI decide which actions to expose without
    # reimplementing the role-tier logic in the browser. Values are
    # "admin", "writer", "viewer" or "none".
    enriched.setdefault("effective_role", effective_role(user_info))
    return enriched
