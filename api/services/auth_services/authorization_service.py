# api/services/auth_services/authorization_service.py

import logging
from typing import Any, Dict, List

from fastapi import Depends, HTTPException, status

from api.config.swagger_settings import swagger_settings
from api.services.auth_services.get_current_user import get_current_user

logger = logging.getLogger(__name__)


def get_allowed_groups() -> List[str]:
    """
    Get the list of allowed groups from configuration.

    Returns
    -------
    List[str]
        List of allowed group names (lowercase)
    """
    if not swagger_settings.group_names:
        return []
    return [g.strip().lower() for g in swagger_settings.group_names.split(",") if g.strip()]


def check_group_membership(user_info: Dict[str, Any]) -> bool:
    """
    Check if user belongs to any of the configured allowed groups.

    Parameters
    ----------
    user_info : Dict[str, Any]
        User information from authentication service containing roles and groups

    Returns
    -------
    bool
        True if user belongs to at least one allowed group, False otherwise
    """
    if not swagger_settings.enable_group_based_access:
        # If feature is disabled, always allow access
        return True

    allowed_groups = get_allowed_groups()
    if not allowed_groups:
        # No groups configured, deny access
        logger.warning("Group-based access enabled but no GROUP_NAMES configured")
        return False

    user_groups = user_info.get("groups", [])

    # Check if any of the user's groups matches an allowed group
    for group in user_groups:
        if isinstance(group, str) and group.lower() in allowed_groups:
            logger.info(f"User authorized: belongs to allowed group '{group}'")
            return True

    logger.warning(
        f"User denied: does not belong to any allowed group. "
        f"Allowed: {allowed_groups}, User groups: {user_groups}"
    )
    return False


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
        allowed_groups = get_allowed_groups()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Access forbidden: write operations require membership "
                f"in one of these groups: {allowed_groups}"
            ),
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


# Backward compatibility aliases
check_organization_membership = check_group_membership
require_organization_member = require_group_member
