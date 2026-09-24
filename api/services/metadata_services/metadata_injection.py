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


def calculate_md5(input_string: str) -> str:
    """
    Generate MD5 hash for catalog alignment.

    This function replicates the hashing algorithm used by the official
    NDP catalog (ckanext-ndpcatalogadditions) to ensure metadata alignment.

    Parameters
    ----------
    input_string : str
        The string to hash (typically the user's 'sub' field from Keycloak).

    Returns
    -------
    str
        A 32-character hexadecimal MD5 hash.
    """
    return hashlib.md5(input_string.encode("utf-8")).hexdigest()


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
    - ndp_user_id: Hashed user identifier (16-character hex, SHA-256)
    - ndp_creator_md5: MD5 hash for catalog alignment (32-character hex)
    """
    if extras is None:
        extras = {}

    # Create a copy to avoid modifying the original dictionary
    updated_extras = extras.copy()

    # Get user sub for hashing
    user_sub = user_info.get("sub", "unknown")

    # Add NDP metadata fields
    updated_extras.update(
        {
            "ndp_group_id": swagger_settings.organization,
            "ndp_user_id": hash_user_id(user_info),
            "ndp_creator_md5": calculate_md5(user_sub),
        }
    )

    return updated_extras


#: Extras the Endpoint owns and writes itself. They identify who created a
#: dataset — ``ndp_creator_md5`` is the hash the NDP catalog matches against
#: — so they must not be settable from outside.
NDP_MANAGED_EXTRAS = frozenset({"ndp_creator_md5", "ndp_user_id", "ndp_group_id"})


def preserve_ndp_metadata(
    current_extras: Dict[str, Any], incoming_extras: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    Merge caller-supplied extras over the stored ones, keeping identity.

    The update services merge with the incoming values winning, which let
    any caller rewrite the creator hash by sending it in ``extras`` — the
    dataset then reported a creator who never touched it (issue #272).
    The keys in :data:`NDP_MANAGED_EXTRAS` are therefore dropped from the
    incoming side and whatever is stored survives. A dataset that carries
    no hash acquires none: filling it in here would record the editor as
    the creator.

    Dropping is silent rather than a 400, because clients routinely read a
    dataset and send its extras back unchanged; the stored value is kept
    either way. The NDP catalog plugin behaves the same way.

    Parameters
    ----------
    current_extras : Dict[str, Any]
        Extras already stored on the dataset, as a key/value mapping.
    incoming_extras : Dict[str, Any], optional
        Extras supplied by the caller.

    Returns
    -------
    Dict[str, Any]
        The merged mapping, with the Endpoint-owned keys untouched.
    """
    merged = dict(current_extras or {})
    for key, value in (incoming_extras or {}).items():
        if key in NDP_MANAGED_EXTRAS:
            continue
        merged[key] = value
    return merged
