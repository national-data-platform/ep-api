# api/routes/user_routes/oidc_exchange.py
"""
Exchange an identity-provider authorization code for an access token.

The browser starts the Authorization Code flow and comes back with a code,
but the exchange happens here rather than in the page. That is what lets a
confidential client be used: `OIDC_CLIENT_SECRET` stays on the Endpoint.

A Federation registration creates a confidential client per Endpoint and
returns its id and secret, so this is the path that makes identity-provider
sign-in work with what a registration already provides. A public client goes
through the same route with no secret configured, and no client
authentication is sent.
"""

import logging
from typing import Any, Dict

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from api.config.oidc_settings import oidc_settings

logger = logging.getLogger(__name__)

router = APIRouter()

DISCOVERY_PATH = "/.well-known/openid-configuration"


class OIDCExchangeRequest(BaseModel):
    """What the browser brings back from the identity provider."""

    code: str = Field(..., description="Authorization code from the provider")
    redirect_uri: str = Field(
        ..., description="The redirect URI the code was issued for"
    )
    code_verifier: str = Field(..., description="PKCE verifier for this exchange")


async def _token_endpoint(client: httpx.AsyncClient) -> str:
    """Read the token endpoint from the realm's discovery document."""
    issuer = oidc_settings.issuer.rstrip("/")
    response = await client.get(f"{issuer}{DISCOVERY_PATH}", timeout=15)

    if response.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail=(
                "Could not reach the identity provider "
                f"(HTTP {response.status_code}). Check OIDC_ISSUER."
            ),
        )

    endpoint = response.json().get("token_endpoint")
    if not endpoint:
        raise HTTPException(
            status_code=502,
            detail="The identity provider's discovery document has no token endpoint.",
        )
    return endpoint


@router.post(
    "/user/oidc/exchange",
    response_model=Dict[str, Any],
    summary="Exchange an identity-provider authorization code for a token",
    description=(
        "Completes the Authorization Code flow started by the UI's "
        "'sign in through the identity provider' button.\n\n"
        "The exchange is performed by the Endpoint rather than the browser, "
        "so a confidential client can be used without its secret ever "
        "reaching the page. The client secret is never returned.\n\n"
        "Only the access token and its type are returned; validation of that "
        "token happens through the usual `/user/info` path."
    ),
    responses={
        200: {"description": "The provider issued a token"},
        400: {"description": "The provider rejected the code"},
        502: {"description": "The identity provider could not be reached"},
        503: {"description": "Identity-provider sign-in is not configured"},
    },
    tags=["User"],
)
async def exchange_oidc_code(payload: OIDCExchangeRequest) -> Dict[str, Any]:
    """
    Exchange an authorization code for an access token.

    Returns
    -------
    dict
        ``access_token``, ``token_type`` and ``expires_in`` as issued by the
        provider. Refresh tokens are deliberately not passed on: the UI holds
        the access token only, as it does for the other sign-in methods.
    """
    if not oidc_settings.is_configured:
        raise HTTPException(
            status_code=503,
            detail="Identity-provider sign-in is not configured on this Endpoint.",
        )

    form = {
        "grant_type": "authorization_code",
        "client_id": oidc_settings.client_id,
        "code": payload.code,
        "redirect_uri": payload.redirect_uri,
        "code_verifier": payload.code_verifier,
    }

    # Only for a confidential client. A public one sends no client
    # authentication at all, which is what the browser used to do.
    if oidc_settings.client_secret:
        form["client_secret"] = oidc_settings.client_secret

    try:
        async with httpx.AsyncClient() as client:
            token_endpoint = await _token_endpoint(client)
            response = await client.post(
                token_endpoint,
                data=form,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=20,
            )
    except HTTPException:
        raise
    except httpx.RequestError as error:
        logger.error(f"Could not reach the identity provider: {error}")
        raise HTTPException(
            status_code=502,
            detail="Could not reach the identity provider to complete sign-in.",
        )

    data = response.json() if response.content else {}

    if response.status_code != 200 or not data.get("access_token"):
        # The provider's own wording is the useful part; the client secret is
        # never echoed back, and nothing from the request is logged.
        detail = (
            data.get("error_description")
            or data.get("error")
            or (
                f"The identity provider did not issue a token (HTTP {response.status_code})."
            )
        )
        logger.warning(f"Identity-provider token exchange failed: {detail}")
        raise HTTPException(status_code=400, detail=detail)

    return {
        "access_token": data["access_token"],
        "token_type": data.get("token_type", "Bearer"),
        "expires_in": data.get("expires_in"),
    }
