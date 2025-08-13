# api/services/metadata_services/metadata_injection.py

import hashlib
from typing import Any, Dict

from api.config.swagger_settings import swagger_settings


def hash_user_id(user_info: Dict[str, Any]) -> str:
    """
    Generate a hash from user's sub field.

    Parameters
    ----------
    user_info : Dict[str, Any]
        User information dictionary containing the 'sub' field.

    Returns
    -------
    str
        A 16-character hexadecimal hash of the user's sub field.
    """
    user_sub = user_info.get("sub", "unknown")
    return hashlib.sha256(user_sub.encode()).hexdigest()[:16]


def inject_ndp_metadata(
    user_info: Dict[str, Any], extras: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    Inject NDP metadata fields into extras dictionary.

    This function automatically adds standardized NDP (National Data
    Platform) metadata fields to the extras dictionary for consistent
    tracking and identification of datasets.

    Parameters
    ----------
    user_info : Dict[str, Any]
        User information dictionary from authentication service.
    extras : Dict[str, Any], optional
        Existing extras dictionary. If None, creates a new dictionary.

    Returns
    -------
    Dict[str, Any]
        Extras dictionary with injected NDP metadata fields.

    Notes
    -----
    The following fields are automatically injected:
    - ndp_group_id: Organization name from configuration
    - ndp_user_id: Hashed user identifier (16-character hex)
    """
    if extras is None:
        extras = {}

    # Create a copy to avoid modifying the original dictionary
    updated_extras = extras.copy()

    # Add NDP metadata fields
    updated_extras.update(
        {
            "ndp_group_id": swagger_settings.organization,
            "ndp_user_id": hash_user_id(user_info),
        }
    )

    return updated_extras
