# api/services/auth_services/authorization_service.py

import logging
from typing import Any, Dict, List

from fastapi import Depends, HTTPException, status

from api.config.affinities_settings import affinities_settings
from api.config.swagger_settings import swagger_settings
from api.services.auth_services.get_current_user import get_current_user

logger = logging.getLogger(__name__)

# Role that always grants access when group-based access is enabled.
ADMIN_ROLE_NAME = "ndp_admin"


def endpoint_admin_role_name() -> str:
    """
    Return the endpoint-specific admin role name derived from the configured
    ``AFFINITIES_EP_UUID``, e.g. ``96207a63-...-002330_admin``. Returns an
    empty string when the UUID is not configured.
    """
    ep_uuid = (affinities_settings.ep_uuid or "").strip()
    if not ep_uuid:
        return ""
    return f"{ep_uuid}_admin"


def normalize_group_path(path: str) -> str:
    """
    Normalize a group path for comparison.

    Removes leading/trailing slashes and converts to lowercase.

    Parameters
    ----------
    path : str
        The group path to normalize

    Returns
    -------
    str
        Normalized path
    """
    return path.strip().strip("/").lower()


def get_allowed_groups() -> List[str]:
    """
    Get the list of allowed groups from configuration.

    Returns
    -------
    List[str]
        List of allowed group names (normalized - lowercase, no leading slashes)
    """
    if not swagger_settings.group_names:
        return []
    return [
        normalize_group_path(g)
        for g in swagger_settings.group_names.split(",")
        if g.strip()
    ]


def _iter_normalized_user_groups(user_info: Dict[str, Any]):
    """
    Yield normalized group values from a user info payload.

    Accepts both plain strings and dicts with ``path``/``name`` fields,
    mirroring the shapes returned by the identity provider. Non-string
    entries with no usable value are skipped.
    """
    for group in user_info.get("groups", []):
        if isinstance(group, str):
            value = normalize_group_path(group)
        elif isinstance(group, dict):
            value = normalize_group_path(
                str(group.get("path") or group.get("name") or "")
            )
        else:
            continue

        if value:
            yield value


def _has_admin_role(user_info: Dict[str, Any]) -> bool:
    """
    Return True if the user has the platform-wide admin role.
    """
    roles = user_info.get("roles", [])
    if not isinstance(roles, list):
        return False
    return any(
        isinstance(role, str) and role.strip().lower() == ADMIN_ROLE_NAME
        for role in roles
    )


def _is_member_of_endpoint_group(user_info: Dict[str, Any]) -> bool:
    """
    Return True if the user belongs to the group matching AFFINITIES_EP_UUID.
    """
    ep_uuid = (affinities_settings.ep_uuid or "").strip()
    if not ep_uuid:
        return False

    target = normalize_group_path(ep_uuid)
    return any(value == target for value in _iter_normalized_user_groups(user_info))


def check_group_membership(user_info: Dict[str, Any]) -> bool:
    """
    Check whether the user is authorized when group-based access is enabled.

    The user is authorized if **any** of the following is true:

    1. Feature disabled (``ENABLE_GROUP_BASED_ACCESS`` is False) — always allow.
    2. User belongs to one of the groups listed in ``GROUP_NAMES``.
    3. User has the ``ndp_admin`` role.
    4. User belongs to the group whose name matches ``AFFINITIES_EP_UUID``.

    Parameters
    ----------
    user_info : Dict[str, Any]
        User information from authentication service containing roles and groups

    Returns
    -------
    bool
        True if the user is authorized, False otherwise.
    """
    if not swagger_settings.enable_group_based_access:
        # If feature is disabled, always allow access
        return True

    # Admin role short-circuits every other check.
    if _has_admin_role(user_info):
        logger.info(f"User authorized: has '{ADMIN_ROLE_NAME}' role")
        return True

    # Membership in the endpoint's own UUID group is always allowed.
    if _is_member_of_endpoint_group(user_info):
        logger.info(
            "User authorized: belongs to endpoint group "
            f"'{affinities_settings.ep_uuid}'"
        )
        return True

    allowed_groups = get_allowed_groups()
    user_groups = user_info.get("groups", [])

    if not allowed_groups:
        logger.warning(
            "Group-based access enabled but no GROUP_NAMES configured, "
            "and user is neither admin nor endpoint member"
        )
        return False

    # Check if any of the user's groups matches an allowed group
    for group_value in _iter_normalized_user_groups(user_info):
        logger.info(f"checking group: {group_value}")
        if group_value in allowed_groups:
            logger.info(f"User authorized: belongs to allowed group '{group_value}'")
            return True

    logger.warning(
        f"User denied: does not belong to any allowed group. "
        f"Allowed: {allowed_groups}, User groups: {user_groups}"
    )
    return False


def _raise_forbidden(user_message: str) -> None:
    """
    Raise the 403 error shared by every authorization dependency.

    The response body shows ``user_message`` only — the technical details
    of the access rule (admin role name, endpoint UUID, configured
    ``GROUP_NAMES``) are written to the application log so administrators
    can still debug rejections without leaking jargon to end users.

    Parameters
    ----------
    user_message : str
        End-user-friendly message surfaced verbatim in the 403 response.
    """
    logger.warning(
        "Access denied (403). Required: role '%s', endpoint group '%s', "
        "or one of %s.",
        ADMIN_ROLE_NAME,
        affinities_settings.ep_uuid,
        get_allowed_groups(),
    )
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=user_message,
    )


def require_group_member(
    user_info: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Dependency that ensures the user belongs to one of the allowed groups.

    This dependency should be used on POST, PUT, DELETE endpoints when
    group-based access control is enabled.

    Parameters
    ----------
    user_info : Dict[str, Any]
        User information from get_current_user dependency

    Returns
    -------
    Dict[str, Any]
        User information if authorized

    Raises
    ------
    HTTPException
        403 Forbidden if user is not authorized for write operations
    """
    if not check_group_membership(user_info):
        _raise_forbidden(
            "You do not have permission to perform this operation. "
            "Please contact the administrator."
        )

    return user_info


def get_user_for_write_operation(
    user_info: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Get current user and check group membership for write operations.

    This is the main dependency to use on POST, PUT, DELETE endpoints.
    It will:
    1. Always require authentication
    2. If group-based access is enabled, check membership in allowed groups
    3. If group-based access is disabled, allow all authenticated users

    Parameters
    ----------
    user_info : Dict[str, Any]
        User information from get_current_user dependency

    Returns
    -------
    Dict[str, Any]
        User information if authorized

    Raises
    ------
    HTTPException
        401 Unauthorized if not authenticated
        403 Forbidden if group-based access is enabled and user
        is not a member of any allowed group
    """
    if swagger_settings.enable_group_based_access:
        return require_group_member(user_info)
    else:
        # Feature disabled, just return authenticated user
        return user_info


def get_user_for_endpoint_access(
    user_info: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Dependency that gates entry to the Endpoint (UI and user-facing APIs).

    Used by ``/user/info`` so the UI's AuthGuard can detect unauthorized
    users at login time and refuse to let them enter the application.

    Behavior mirrors :func:`get_user_for_write_operation` but the 403
    error message refers to "access to this Endpoint" instead of
    "write operations".

    Parameters
    ----------
    user_info : Dict[str, Any]
        User information from :func:`get_current_user`.

    Returns
    -------
    Dict[str, Any]
        User information if authorized.

    Raises
    ------
    HTTPException
        403 Forbidden if group-based access is enabled and the user is
        not authorized to access this Endpoint.
    """
    if not swagger_settings.enable_group_based_access:
        return user_info

    if not check_group_membership(user_info):
        _raise_forbidden(
            "You do not have permission to access this Endpoint. "
            "Please contact the administrator."
        )

    return user_info


def is_admin(user_info: Dict[str, Any]) -> bool:
    """
    Return True if the user has either the ``ndp_admin`` role or the
    endpoint-specific admin role (``{AFFINITIES_EP_UUID}_admin``).
    """
    if _has_admin_role(user_info):
        return True

    ep_admin_role = endpoint_admin_role_name()
    if not ep_admin_role:
        return False

    roles = user_info.get("roles", [])
    if not isinstance(roles, list):
        return False

    target = ep_admin_role.strip().lower()
    return any(
        isinstance(role, str) and role.strip().lower() == target for role in roles
    )


def require_admin(
    user_info: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Dependency that enforces an administrator role on the caller.

    Grants access to users with the realm role ``ndp_admin`` or the
    endpoint-specific admin role ``{AFFINITIES_EP_UUID}_admin``. Any
    other authenticated user is rejected with 403.
    """
    if is_admin(user_info):
        return user_info

    logger.warning(
        "Admin-only action denied for user '%s' (sub=%s). Required roles: "
        "'%s' or '%s'.",
        user_info.get("username"),
        user_info.get("sub"),
        ADMIN_ROLE_NAME,
        endpoint_admin_role_name() or "<unset>",
    )
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Administrator role required.",
    )


# Backward compatibility aliases
check_organization_membership = check_group_membership
require_organization_member = require_group_member
