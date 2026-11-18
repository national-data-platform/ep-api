# api/services/auth_services/aai_client.py
"""
Thin client for the NDP AAI API (``aai_api_url``).

The AAI API is authoritative for group and role writes in Keycloak. This
module wraps what access-request approval needs: a client-credentials token
for the Endpoint's own client, and adding a user to a group at a permission
level. It also lists group members.

Group calls carry the approving administrator's own bearer token: the AAI
lets a user change a group only when they are in its ``admins`` subgroup (or
an ancestor's) or hold ``ndp_admin``. For a group under ``ndp_ep`` it also
wants proof that the calling app is that Endpoint's own client, sent as
``X-Client-Assertion: Bearer <client-credentials token>``.
"""

import logging
from typing import Any, Dict, Optional

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

    # The caller's token was already accepted by this Endpoint, so a 400 or
    # 401 from the AAI is about the request the Endpoint built or the
    # client assertion it sent (a configuration problem), not the user's
    # session. Answering 401 would make the UI sign the admin out.
    if response.status_code in (400, 401):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Authentication service refused the request: {detail}",
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


def _post(
    path: str,
    admin_token: str,
    payload: Dict[str, Any],
    client_assertion: Optional[str] = None,
) -> Dict[str, Any]:
    url = f"{swagger_settings.aai_api_url}{path}"
    headers = {"Authorization": f"Bearer {admin_token}"}
    if client_assertion:
        headers["X-Client-Assertion"] = f"Bearer {client_assertion}"
    try:
        response = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=15,
        )
    except requests.exceptions.RequestException as exc:
        logger.error(f"AAI POST {url} failed: {exc}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Authentication service is unavailable.",
        )

    # 207 is the AAI's "partial success": some users were not added.
    if 200 <= response.status_code < 300 and response.status_code != 207:
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


def client_login(client_id: str, secret: str) -> str:
    """
    Return a client-credentials access token for ``client_id``, from
    ``POST /client/login``, to send as ``X-Client-Assertion``.

    A refusal means this Endpoint's service-client settings are wrong, not
    that anyone's session is, so it answers 503 rather than 401.
    """
    url = f"{swagger_settings.aai_api_url}/client/login"
    try:
        response = requests.post(
            url,
            json={"client_id": client_id, "secret": secret},
            timeout=15,
        )
    except requests.exceptions.RequestException as exc:
        logger.error(f"AAI POST {url} failed: {exc}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Authentication service is unavailable.",
        )

    if response.status_code in (400, 401):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "The authentication service refused this Endpoint's service "
                f"client '{client_id}'; check OIDC_SERVICE_CLIENT_ID and "
                "OIDC_SERVICE_CLIENT_SECRET."
            ),
        )
    if response.status_code == 200:
        try:
            token = response.json().get("access_token")
        except (ValueError, AttributeError):
            token = None
        if token:
            return token
    raise HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail=(
            f"Authentication service returned HTTP {response.status_code} "
            "when signing in this Endpoint's service client."
        ),
    )


def add_user_to_group(
    admin_token: str,
    group_name: str,
    user: str,
    role: str = "viewer",
    client_assertion: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Add ``user`` (a Keycloak user id or an email) to ``group_name`` at
    ``role``, one of the group's permission levels (``admin``, ``editor``
    or ``viewer``).

    The AAI assigns the realm role ``group:<group>:<role>`` and puts the
    user in the level's subgroup ``<group>/<role>s``, which the Endpoint's
    gates are decided on. It accepts ``admin_token`` when its holder is in
    the group's ``admins`` subgroup, or an ancestor's, or holds
    ``ndp_admin``. For a group under ``ndp_ep`` it also needs
    ``client_assertion``, a client-credentials token of that group's own
    client (``ep-1`` for ``ndp_ep/ep-1``), unless the caller holds
    ``ndp_admin``. AAI versions that do not check the calling app ignore it.
    """
    return _post(
        "/group/add-user",
        admin_token,
        {"groupName": group_name, "user": user, "role": role},
        client_assertion=client_assertion,
    )


def list_group_members(admin_token: str, group_name: str) -> Dict[str, Any]:
    """Return the members of ``group_name`` as reported by the AAI API."""
    payload = _get(
        "/group/members",
        admin_token,
        {"groupName": group_name},
    )
    # The AAI returns {} when the group is empty, and a mapping otherwise.
    return payload or {}
