# api/services/auth_services/legacy_roles.py
"""
COMPATIBILITY SHIM (issue #433): permission decisions for Endpoint clients
that have no permission gates.

Keycloak decides the gates (``admin-area``, ``editor-area``, ``viewer-area``)
only on clients created by Federation 2.0.0 or later, or adopted with the
Federation's ``adopt_client.py``. A client from Federation 1.x answers the
gate request with "Client does not support permissions"; for it, the
Endpoint decides as releases before the gates did, from the realm roles and
groups in the user's information:

- ``admin-area``: ``ndp_admin``, or ``group:<group>:admin``;
- ``editor-area``: the above, ``ndp_writer``/``ndp_editor``, or
  ``group:<group>:writer``/``group:<group>:editor``;
- ``viewer-area``: the above, ``ndp_viewer``, ``group:<group>:viewer``, or
  membership of ``<group>`` (which let users into the Endpoint before).

``<group>`` is the Endpoint's group, ``ndp_ep/<OIDC_SERVICE_CLIENT_ID>``,
and each ``GROUP_NAMES`` entry.

Remove this module, and its use in ``ep_access_gate``, once every Endpoint
client has gates (see docs/compatibility-shims.md).
"""

from typing import Any, Dict, Iterable, List, Set

from api.config.swagger_settings import swagger_settings

_PLATFORM_ROLES = {
    "admin-area": {"ndp_admin"},
    "editor-area": {"ndp_admin", "ndp_writer", "ndp_editor"},
    "viewer-area": {"ndp_admin", "ndp_writer", "ndp_editor", "ndp_viewer"},
}

_GROUP_LEVELS = {
    "admin-area": ("admin",),
    "editor-area": ("admin", "writer", "editor"),
    "viewer-area": ("admin", "writer", "editor", "viewer"),
}


def _normalize(path: str) -> str:
    return path.strip().strip("/").lower()


def endpoint_groups() -> List[str]:
    """The Endpoint's group and each GROUP_NAMES entry, normalized."""
    groups = []
    if swagger_settings.oidc_service_client_id:
        groups.append(_normalize(f"ndp_ep/{swagger_settings.oidc_service_client_id}"))
    for name in (swagger_settings.group_names or "").split(","):
        if name.strip():
            groups.append(_normalize(name))
    return list(dict.fromkeys(groups))


def _role(value: str) -> str:
    value = value.strip().lower()
    if value.startswith("group:") and ":" in value[len("group:") :]:
        path, level = value[len("group:") :].rsplit(":", 1)
        return f"group:{_normalize(path)}:{level.strip()}"
    return value


def _roles(user_info: Dict[str, Any]) -> Set[str]:
    roles = user_info.get("roles") or []
    if not isinstance(roles, list):
        return set()
    return {_role(role) for role in roles if isinstance(role, str)}


def _groups(user_info: Dict[str, Any]) -> Iterable[str]:
    for group in user_info.get("groups") or []:
        if isinstance(group, str):
            value = group
        elif isinstance(group, dict):
            value = str(group.get("path") or group.get("name") or "")
        else:
            continue
        if value.strip():
            yield _normalize(value)


def passes(user_info: Dict[str, Any], gate: str) -> bool:
    """Whether ``user_info`` would have passed ``gate`` before the gates."""
    if gate not in _GROUP_LEVELS:
        return False
    roles = _roles(user_info)
    if roles & _PLATFORM_ROLES[gate]:
        return True
    groups = endpoint_groups()
    wanted = {
        f"group:{group}:{level}" for group in groups for level in _GROUP_LEVELS[gate]
    }
    if roles & wanted:
        return True
    if gate == "viewer-area":
        # Membership of the group, or of one of its level subgroups.
        for value in _groups(user_info):
            if any(value == g or value.startswith(f"{g}/") for g in groups):
                return True
    return False
