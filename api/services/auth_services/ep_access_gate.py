# api/services/auth_services/ep_access_gate.py
"""
Permission gates for the Endpoint's protected routes.

The Endpoint's Keycloak client (OIDC_SERVICE_CLIENT_ID, ``ep-<config-id>``) has
three gates, set up by the AAI API from the Endpoint's group:
``admin-area`` (its admins), ``editor-area`` (admins and editors) and
``viewer-area`` (admins, editors and viewers); ``ndp_admin`` passes all
three on a client the AAI created with ``/client/create``. :func:`ep_access_gate` makes the same decision call as the
Federation's ``app/services/ep_access_gate.py``; the three ``ep_*_gate``
functions are the route dependencies built on it.

COMPATIBILITY SHIM (issue #433): a client created by Federation 1.x has no
gates, and Keycloak answers "Client does not support permissions". Such an
Endpoint decides from the user's roles instead, as before the gates (see
:mod:`legacy_roles`), so it keeps working until its client is adopted.
"""

import logging
from typing import Any, Dict, Optional

import requests
from fastapi import Depends, HTTPException, status

from api.config.swagger_settings import swagger_settings
from api.services.auth_services import legacy_roles
from api.services.auth_services.get_current_user import get_current_user, security

logger = logging.getLogger(__name__)

_UMA_GRANT = "urn:ietf:params:oauth:grant-type:uma-ticket"

# What Keycloak answers when the client has no gates (#433): a client without
# authorization services, or one with them but without the gate resources.
_NO_GATES = ("Client does not support permissions",)
_NO_GATES_ERRORS = ("invalid_resource",)

_warned_no_gates = False


def _client_has_no_gates(response) -> bool:
    if response.status_code != 400:
        return False
    try:
        body = response.json()
    except ValueError:
        return False
    if not isinstance(body, dict):
        return False
    return body.get("error") in _NO_GATES_ERRORS or any(
        text in str(body.get("error_description", "")) for text in _NO_GATES
    )


def _warn_no_gates() -> None:
    global _warned_no_gates
    if not _warned_no_gates:
        _warned_no_gates = True
        logger.warning(
            "Keycloak client '%s' has no permission gates (created by "
            "Federation 1.x); deciding from the user's roles instead. Adopt "
            "the client to use the gates (issue #433).",
            swagger_settings.oidc_service_client_id,
        )


def keycloak_decision(token: str, gate: str) -> Optional[bool]:
    """
    Ask Keycloak whether the token's user passes ``gate`` on this Endpoint's
    client: True or False, or None when the client has no gates (#433).

    Raises 401 when Keycloak rejects the token and 502 when it is
    unreachable or fails.
    """
    token_url = swagger_settings.keycloak_token_url
    try:
        response = requests.post(
            token_url,
            headers={"Authorization": f"Bearer {token}"},
            data={
                "grant_type": _UMA_GRANT,
                "audience": swagger_settings.oidc_service_client_id,
                "permission": gate,
                "response_mode": "decision",
            },
            timeout=10,
        )
    except requests.RequestException as e:
        logger.error("Keycloak unreachable at %s: %s", token_url, e)
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
    if _client_has_no_gates(response):
        return None
    try:
        return response.status_code == 200 and response.json() == {"result": True}
    except ValueError:
        return False


def ep_access_gate(
    token: str, gate: str, user_info: Optional[Dict[str, Any]] = None
) -> None:
    """
    Raise unless Keycloak lets the token's user through ``gate`` on this
    Endpoint's client. TEST_TOKEN, when set, passes every gate without asking.

    On a client without gates (#433) the decision comes from ``user_info``'s
    roles instead (:mod:`legacy_roles`); without ``user_info`` it is a denial.

    401: Keycloak rejects the token. 403: anything but a grant, including
    when OIDC_SERVICE_CLIENT_ID is not set. 502: Keycloak is unreachable or fails.
    """
    if swagger_settings.test_token and token == swagger_settings.test_token:
        return
    denied = HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=f"This token does not pass {gate} on this Endpoint",
    )
    if not swagger_settings.oidc_service_client_id:
        raise denied

    decision = keycloak_decision(token, gate)
    if decision is None:
        _warn_no_gates()
        decision = user_info is not None and legacy_roles.passes(user_info, gate)
    if not decision:
        raise denied


def ep_admin_gate(
    user_info: Dict[str, Any] = Depends(get_current_user),
    token_data=Depends(security),
) -> Dict[str, Any]:
    """Let admins of the Endpoint through; returns the user."""
    ep_access_gate(token_data.credentials, "admin-area", user_info)
    return user_info


def ep_editor_gate(
    user_info: Dict[str, Any] = Depends(get_current_user),
    token_data=Depends(security),
) -> Dict[str, Any]:
    """Let editors and admins of the Endpoint through; returns the user."""
    ep_access_gate(token_data.credentials, "editor-area", user_info)
    return user_info


def ep_viewer_gate(
    user_info: Dict[str, Any] = Depends(get_current_user),
    token_data=Depends(security),
) -> Dict[str, Any]:
    """Let viewers, editors and admins of the Endpoint through; returns the user."""
    ep_access_gate(token_data.credentials, "viewer-area", user_info)
    return user_info
