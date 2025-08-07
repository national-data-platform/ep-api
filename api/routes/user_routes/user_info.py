# api/routes/user_routes/user_info.py

from typing import Any, Dict

from fastapi import APIRouter, Depends

from api.services.auth_services import get_current_user

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
    user_info: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Get current user information from the authentication service.

    This endpoint acts as a passthrough to the authentication service,
    returning the complete user profile information that was retrieved
    during token validation.

    Parameters
    ----------
    user_info : Dict[str, Any]
        User information from get_current_user dependency

    Returns
    -------
    Dict[str, Any]
        Complete user information as returned by the authentication service

    Raises
    ------
    HTTPException
        401: If token is invalid or expired
        403: If token does not have sufficient permissions
        502: If authentication service is unavailable
    """
    return user_info
