# api/routes/user_routes/user_login.py

from typing import Any, Dict

from fastapi import APIRouter

from api.models.token_model import UserLoginRequest
from api.services.auth_services import authenticate_with_credentials

router = APIRouter()


@router.post(
    "/user/login",
    response_model=Dict[str, Any],
    summary="Authenticate user with username and password",
    description=(
        "Authenticate a user with username and password against the "
        "identity provider.\n\n"
        "On success, the endpoint returns the access token together with "
        "any additional profile information provided by the authentication "
        "service (roles, groups, token type, etc.).\n\n"
        "### Example Request\n"
        "```json\n"
        "{\n"
        '  "username": "john.doe",\n'
        '  "password": "s3cret"\n'
        "}\n"
        "```\n\n"
        "### Example Response\n"
        "```json\n"
        "{\n"
        '  "access_token": "eyJhbGciOi...",\n'
        '  "token_type": "Bearer",\n'
        '  "roles": ["user"],\n'
        '  "groups": []\n'
        "}\n"
        "```\n"
    ),
    responses={
        200: {
            "description": "Authentication successful",
            "content": {
                "application/json": {
                    "example": {
                        "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                        "token_type": "Bearer",
                        "roles": ["user"],
                        "groups": [],
                    }
                }
            },
        },
        401: {
            "description": "Invalid credentials",
            "content": {
                "application/json": {
                    "example": {"detail": "Invalid username or password"}
                }
            },
        },
        502: {
            "description": "Authentication service unavailable",
            "content": {
                "application/json": {
                    "example": {"detail": "Authentication service is unavailable."}
                }
            },
        },
    },
)
async def user_login(payload: UserLoginRequest) -> Dict[str, Any]:
    """
    Authenticate a user with username and password.

    This endpoint proxies the credentials to the configured identity
    provider and returns the resulting access token and profile data.

    Parameters
    ----------
    payload : UserLoginRequest
        The username and password to authenticate.

    Returns
    -------
    Dict[str, Any]
        The authentication response from the identity provider, including
        the access token.

    Raises
    ------
    HTTPException
        401: If the credentials are invalid.
        502: If the authentication service is unavailable.
    """
    return authenticate_with_credentials(payload.username, payload.password)
