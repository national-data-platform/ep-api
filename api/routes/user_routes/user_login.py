# api/routes/user_routes/user_login.py

from typing import Any, Dict

from fastapi import APIRouter, Form

from api.models.token_model import OidcCodeExchangeRequest, UserLoginRequest
from api.services.auth_services import (
    authenticate_with_credentials,
    exchange_authorization_code,
)

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


@router.post(
    "/token",
    response_model=Dict[str, Any],
    summary="Authenticate with form-encoded credentials (compatibility alias)",
    description=(
        "Compatibility alias for `/user/login`. Existing clients — such as "
        "already-installed versions of the `ndp-ep` Python library — post "
        "form-encoded `username` and `password` to `/token`. This route "
        "accepts that form and returns the same result as `/user/login`, so "
        "those clients keep working without any change on their side.\n\n"
        "New integrations should use `POST /user/login` with a JSON body."
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
        401: {"description": "Invalid credentials"},
        502: {"description": "Authentication service unavailable"},
    },
)
async def token(
    username: str = Form(...),
    password: str = Form(...),
) -> Dict[str, Any]:
    """
    Authenticate with form-encoded credentials.

    This is a thin compatibility wrapper around the same authentication used
    by ``/user/login``; the only difference is that the credentials arrive as
    form fields rather than JSON, which is what existing clients send.

    Parameters
    ----------
    username : str
        The username to authenticate, from a form field.
    password : str
        The password to authenticate, from a form field.

    Returns
    -------
    Dict[str, Any]
        The authentication response from the identity provider, including
        the access token.
    """
    return authenticate_with_credentials(username, password)


@router.post(
    "/user/oidc/token",
    response_model=Dict[str, Any],
    summary="Finish signing in on the identity provider's page",
    description=(
        "The last step of signing in on the identity provider's own login "
        "page with this Endpoint's service client (`OIDC_SERVICE_CLIENT_ID`). "
        "The UI sends the authorization code the provider sent back and, "
        "when the sign-in used PKCE, its verifier; the Endpoint redeems the "
        "code with the client's secret, which never reaches the browser, for "
        "`OIDC_REDIRECT_URI` only, and returns the access token.\n\n"
        "Answers 503 unless `OIDC_ENABLED`, `OIDC_REDIRECT_URI`, "
        "`OIDC_SERVICE_CLIENT_ID` and `OIDC_SERVICE_CLIENT_SECRET` are all set."
    ),
    responses={
        200: {
            "description": "Signed in",
            "content": {
                "application/json": {
                    "example": {
                        "access_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...",
                        "token_type": "Bearer",
                        "expires_in": 18000,
                    }
                }
            },
        },
        400: {"description": "The identity provider refused the code"},
        502: {"description": "The identity provider is unavailable"},
        503: {
            "description": (
                "Not set up on this Endpoint, or the identity provider "
                "refused its client"
            )
        },
    },
)
async def oidc_token(payload: OidcCodeExchangeRequest) -> Dict[str, Any]:
    """Redeem an authorization code with the Endpoint's service client."""
    return exchange_authorization_code(payload.code, payload.code_verifier)
