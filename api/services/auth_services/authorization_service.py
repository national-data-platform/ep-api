# api/services/auth_services/authorization_service.py

import logging
from typing import Any, Dict

from fastapi import Depends, HTTPException, status

from api.config.swagger_settings import swagger_settings
from api.services.auth_services.get_current_user import get_current_user

logger = logging.getLogger(__name__)


def check_organization_membership(user_info: Dict[str, Any]) -> bool:
    """
    Check if user belongs to the configured organization.

    Parameters
    ----------
    user_info : Dict[str, Any]
        User information from authentication service containing roles and groups

    Returns
    -------
    bool
        True if user belongs to the configured organization, False otherwise
    """
    if not swagger_settings.enable_organization_based_access:
        # If feature is disabled, always allow access
        return True

    configured_org = swagger_settings.organization.lower()
    user_groups = user_info.get("groups", [])

    # Check if any of the user's groups matches the configured organization
    for group in user_groups:
        if isinstance(group, str) and group.lower() == configured_org:
            logger.info(f"User authorized: belongs to organization '{configured_org}'")
            return True

    logger.warning(
        f"User denied: does not belong to organization '{configured_org}'. "
        f"User groups: {user_groups}"
    )
    return False


def require_organization_member(
    user_info: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Dependency that ensures the user belongs to the configured organization.

    This dependency should be used on POST, PUT, DELETE endpoints when
    organization-based access control is enabled.

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
    if not check_organization_membership(user_info):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Access forbidden: write operations require membership "
                f"in organization '{swagger_settings.organization}'"
            ),
        )

    return user_info


def get_user_for_write_operation(
    user_info: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Get current user and check organization membership for write operations.

    This is the main dependency to use on POST, PUT, DELETE endpoints.
    It will:
    1. Always require authentication
    2. If organization-based access is enabled, check membership
    3. If organization-based access is disabled, allow all authenticated users

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
        403 Forbidden if organization-based access is enabled and user
        is not a member
    """
    if swagger_settings.enable_organization_based_access:
        return require_organization_member(user_info)
    else:
        # Feature disabled, just return authenticated user
        return user_info
