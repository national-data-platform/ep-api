# api/services/auth_services/ep_access_gate.py
"""
Permission gates for the Endpoint's protected routes.

The Endpoint's Keycloak client (AUTHZ_CLIENT_ID, ``ep-<config-id>``) has
three gates, set up by the AAI API from the Endpoint's group:
``admin-area`` (its admins), ``editor-area`` (admins and editors) and
``viewer-area`` (admins, editors and viewers); ``ndp_admin`` passes all
three on a client the AAI created with ``/client/create``. :func:`ep_access_gate` makes the same decision call as the
Federation's ``app/services/ep_access_gate.py``; the three ``ep_*_gate``
functions are the route dependencies built on it.
"""

import logging
from typing import Any, Dict

import requests
from fastapi import Depends, HTTPException, status

from api.config.swagger_settings import swagger_settings
from api.services.auth_services.get_current_user import get_current_user, security

logger = logging.getLogger(__name__)

_UMA_GRANT = "urn:ietf:params:oauth:grant-type:uma-ticket"


def ep_access_gate(token: str, gate: str) -> None:
    """
    Raise unless Keycloak lets the token's user through ``gate`` on this
    Endpoint's client. TEST_TOKEN, when set, passes every gate without asking.

    401: Keycloak rejects the token. 403: anything but a grant, including
    when AUTHZ_CLIENT_ID is not set. 502: Keycloak is unreachable or fails.
    """
    if swagger_settings.test_token and token == swagger_settings.test_token:
        return
    denied = HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=f"This token does not pass {gate} on this Endpoint",
    )
    if not swagger_settings.authz_client_id:
        raise denied

    realm = swagger_settings.keycloak_realm_url
    try:
        response = requests.post(
            f"{realm}/protocol/openid-connect/token",
            headers={"Authorization": f"Bearer {token}"},
            data={
                "grant_type": _UMA_GRANT,
                "audience": swagger_settings.authz_client_id,
                "permission": gate,
                "response_mode": "decision",
            },
            timeout=10,
        )
    except requests.RequestException as e:
        logger.error("Keycloak unreachable at %s: %s", realm, e)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The identity provider is unavailable.",
        )

    if response.status_code == 401:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if response.status_code >= 500:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"The identity provider failed (HTTP {response.status_code}).",
        )
    try:
        granted = response.status_code == 200 and response.json() == {"result": True}
    except ValueError:
        granted = False
    if not granted:
        raise denied


def ep_admin_gate(
    user_info: Dict[str, Any] = Depends(get_current_user),
    token_data=Depends(security),
) -> Dict[str, Any]:
    """Let admins of the Endpoint through; returns the user."""
    ep_access_gate(token_data.credentials, "admin-area")
    return user_info


def ep_editor_gate(
    user_info: Dict[str, Any] = Depends(get_current_user),
    token_data=Depends(security),
) -> Dict[str, Any]:
    """Let editors and admins of the Endpoint through; returns the user."""
    ep_access_gate(token_data.credentials, "editor-area")
    return user_info


def ep_viewer_gate(
    user_info: Dict[str, Any] = Depends(get_current_user),
    token_data=Depends(security),
) -> Dict[str, Any]:
    """Let viewers, editors and admins of the Endpoint through; returns the user."""
    ep_access_gate(token_data.credentials, "viewer-area")
    return user_info
