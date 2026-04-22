# api/services/auth_services/user_login.py
import logging
from typing import Any, Dict
from urllib.parse import urlparse

import requests
from fastapi import HTTPException, status

from api.config.swagger_settings import swagger_settings

logger = logging.getLogger(__name__)


def _build_login_url() -> str:
    """
    Derive the IDP login URL from the configured ``auth_api_url``.

    The auth API URL points at the token-information endpoint (e.g.
    ``https://idp.example.com/information``). The login endpoint lives on the
    same server at ``/user/login``.
    """
    parsed = urlparse(swagger_settings.auth_api_url)
    if not parsed.scheme or not parsed.netloc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Authentication service URL is not configured correctly.",
        )
    return f"{parsed.scheme}://{parsed.netloc}/user/login"


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
    login_url = _build_login_url()

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
