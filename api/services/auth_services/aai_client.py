# api/services/auth_services/aai_client.py
"""
Thin client for the NDP AAI API (``aai_api_url``).

The AAI API is authoritative for group and role writes in Keycloak. This
module only exposes the two operations the access-request workflow needs:
adding a user to a group at a permission level and listing group members.

Every call is made on behalf of an already-authenticated ep-api user — the
caller provides the user's bearer token. The AAI API validates the token and
checks the caller's roles (``ndp_admin`` or scoped ``group:<path>:admin``),
so no service account lives on the ep-api side.
"""

import logging
from typing import Any, Dict, List

import requests
from fastapi import HTTPException, status

from api.config.swagger_settings import swagger_settings

logger = logging.getLogger(__name__)


def _forward_aai_error(response: requests.Response, fallback: str) -> None:
    """Translate an AAI error response into an HTTPException for the caller."""
    detail = fallback
    try:
        payload = response.json()
        if isinstance(payload, dict):
            detail = payload.get("detail") or payload.get("error") or fallback
    except ValueError:
        pass

    if response.status_code in (400, 401):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
        )
    if response.status_code == 403:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
        )
    if response.status_code == 404:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail,
        )
    raise HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail=f"Authentication service returned HTTP {response.status_code}.",
    )


def _post(path: str, admin_token: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    url = f"{swagger_settings.aai_api_url}{path}"
    try:
        response = requests.post(
            url,
            headers={"Authorization": f"Bearer {admin_token}"},
            json=payload,
            timeout=15,
        )
    except requests.exceptions.RequestException as exc:
        logger.error(f"AAI POST {url} failed: {exc}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Authentication service is unavailable.",
        )

    if 200 <= response.status_code < 300:
        try:
            return response.json() if response.content else {}
        except ValueError:
            return {}

    _forward_aai_error(response, "Authentication service rejected the request.")
    return {}  # unreachable — _forward_aai_error always raises


def _get(path: str, admin_token: str, params: Dict[str, Any]) -> Any:
    url = f"{swagger_settings.aai_api_url}{path}"
    try:
        response = requests.get(
            url,
            headers={"Authorization": f"Bearer {admin_token}"},
            params=params,
            timeout=15,
        )
    except requests.exceptions.RequestException as exc:
        logger.error(f"AAI GET {url} failed: {exc}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Authentication service is unavailable.",
        )

    if 200 <= response.status_code < 300:
        try:
            return response.json()
        except ValueError:
            return None

    _forward_aai_error(response, "Authentication service rejected the request.")
    return None  # unreachable


def add_user_to_group(
    admin_token: str, group_name: str, username: str, role: str = "viewer"
) -> Dict[str, Any]:
    """
    Add ``username`` to ``group_name`` at ``role``, one of the group's
    permission levels (``admin``, ``editor`` or ``viewer``).

    Uses the admin's own bearer token; the AAI API enforces that the caller
    has ``ndp_admin`` or at least ``editor`` on the target group.
    """
    return _post(
        "/group/add-user",
        admin_token,
        {"group_name": group_name, "username": username, "role": role},
    )


def list_group_members(admin_token: str, group_name: str) -> Dict[str, Any]:
    """Return the members of ``group_name`` as reported by the AAI API."""
    payload = _get(
        "/group/members",
        admin_token,
        {"group_name": group_name},
    )
    # The AAI returns {} when the group is empty, and a mapping otherwise.
    return payload or {}
