# api/services/auth_services/user_login.py
import logging
from typing import Any, Dict, Optional

import requests
from fastapi import HTTPException, status

from api.config.swagger_settings import swagger_settings

logger = logging.getLogger(__name__)


def authenticate_with_credentials(username: str, password: str) -> Dict[str, Any]:
    """
    Authenticate a user with username and password against the IDP.

    Parameters
    ----------
    username : str
        The username to authenticate.
    password : str
        The password to authenticate.

    Returns
    -------
    Dict[str, Any]
        The IDP response, typically including ``access_token``, ``token_type``,
        ``roles`` and ``groups``.

    Raises
    ------
    HTTPException
        401: If credentials are invalid.
        502: If the authentication service is unreachable or misconfigured.
    """
    login_url = f"{swagger_settings.aai_api_url}/user/login"

    try:
        response = requests.post(
            login_url,
            json={"username": username, "password": password},
            timeout=10,
        )
    except requests.exceptions.RequestException as exc:
        logger.error(f"Auth service unreachable at {login_url}: {exc}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Authentication service is unavailable.",
        )

    if response.status_code == 200:
        try:
            data = response.json()
        except ValueError:
            logger.error("Auth service returned non-JSON response")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Authentication service returned an invalid response.",
            )

        if not isinstance(data, dict) or "access_token" not in data:
            logger.error(
                "Auth service response missing 'access_token' field: "
                f"{list(data.keys()) if isinstance(data, dict) else type(data)}"
            )
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Authentication service response is missing access token.",
            )

        return data

    if response.status_code in (400, 401, 403):
        # Forward the IDP's reason when present, fall back to a generic message.
        detail = "Invalid username or password"
        try:
            payload = response.json()
            if isinstance(payload, dict):
                detail = payload.get("error") or payload.get("detail") or detail
        except ValueError:
            pass
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )

    logger.error(
        f"Auth service returned unexpected status {response.status_code}: "
        f"{response.text[:200]}"
    )
    raise HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail=(
            "Authentication service returned an unexpected response "
            f"(HTTP {response.status_code})."
        ),
    )


def exchange_authorization_code(
    code: str, code_verifier: Optional[str] = None
) -> Dict[str, Any]:
    """
    Redeem the authorization code the identity provider's login page sent
    back, as this Endpoint's service client (OIDC_SERVICE_CLIENT_ID), and
    return the access token.

    The client is confidential, so the code is redeemed here, where its
    secret is, and never in the browser. It is redeemed for
    OIDC_REDIRECT_URI only: the clients the Federation creates accept any
    redirect URI, and a code the identity provider sent anywhere else must
    not be redeemable with this Endpoint's secret.

    ``code_verifier`` is the browser's PKCE verifier, which ties the code to
    the tab that started the sign-in. It is None over plain http, where
    browsers cannot compute PKCE: anyone holding the code could then redeem
    it here until the UI does, at once, or it expires (one use, about a
    minute in Keycloak). Over plain http the token itself crosses the
    network unencrypted anyway.

    Only the access token goes back: the UI keeps no refresh token, and one
    of a confidential client is no use without the secret.

    Raises
    ------
    HTTPException
        400: the identity provider refused the code (expired, already used,
             issued for another redirect URI, wrong verifier).
        502: the identity provider is unreachable or answered unexpectedly.
        503: sign-in with the service client is not set up, or the identity
             provider refused the client itself.
    """
    settings = swagger_settings
    client_id = settings.oidc_service_client_id
    secret = settings.oidc_service_client_secret.get_secret_value()
    if not (
        settings.oidc_enabled and client_id and secret and settings.oidc_redirect_uri
    ):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Signing in through the identity provider is not set up on "
                "this Endpoint: it needs OIDC_ENABLED, OIDC_REDIRECT_URI, "
                "OIDC_SERVICE_CLIENT_ID and OIDC_SERVICE_CLIENT_SECRET."
            ),
        )

    token_url = settings.keycloak_token_url
    form = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": settings.oidc_redirect_uri,
        "client_id": client_id,
        "client_secret": secret,
    }
    if code_verifier:
        form["code_verifier"] = code_verifier
    try:
        response = requests.post(token_url, data=form, timeout=10)
    except requests.exceptions.RequestException as exc:
        logger.error(f"Identity provider unreachable at {token_url}: {exc}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The identity provider is unavailable.",
        )

    try:
        data = response.json()
    except ValueError:
        data = {}
    if not isinstance(data, dict):
        data = {}

    if response.status_code == 200 and data.get("access_token"):
        return {
            "access_token": data["access_token"],
            "token_type": data.get("token_type") or "Bearer",
            "expires_in": data.get("expires_in"),
        }

    error = data.get("error") or ""
    if error in ("invalid_client", "unauthorized_client"):
        logger.error(
            f"The identity provider refused service client '{client_id}' "
            f"at {token_url}: {error}"
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "The identity provider refused this Endpoint's client "
                f"'{client_id}'; check OIDC_SERVICE_CLIENT_ID, "
                "OIDC_SERVICE_CLIENT_SECRET, KEYCLOAK_URL and AUTHZ_REALM."
            ),
        )
    if response.status_code in (400, 401):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "The identity provider did not accept the sign-in: "
                f"{data.get('error_description') or error or 'no reason given'}."
                " Please sign in again."
            ),
        )

    logger.error(
        f"Identity provider returned unexpected status {response.status_code} "
        f"at {token_url}"
    )
    raise HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail=(
            "The identity provider returned an unexpected response "
            f"(HTTP {response.status_code})."
        ),
    )
