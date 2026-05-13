# api/services/organization_services/list_organization.py
from typing import Any, Dict, List, Optional

from api.config import catalog_settings


def _extract_ndp_user_id(org: Dict[str, Any]) -> Optional[str]:
    """
    Read ``ndp_user_id`` from a full organization payload, regardless of
    which backend produced it.

    - MongoDB stores it as a top-level field on the org doc.
    - CKAN stores it as a ``{"key": "ndp_user_id", "value": "..."}`` entry
      inside the org's ``extras`` list.
    """
    top_level = org.get("ndp_user_id")
    if top_level:
        return top_level
    for extra in org.get("extras") or []:
        if isinstance(extra, dict) and extra.get("key") == "ndp_user_id":
            return extra.get("value")
    return None


def list_organization(
    name: Optional[str] = None,
    server: str = "global",
    user_hash: Optional[str] = None,
) -> List[str]:
    """
    Retrieve a list of all organizations from the specified catalog,
    optionally filtered by name.

    Parameters
    ----------
    name : Optional[str]
        A string to filter organizations by name (case-insensitive).
    server : str
        The catalog to use. Can be 'local', 'global', or 'pre_ckan'.
        Defaults to 'global'.
    user_hash : Optional[str]
        When provided, only organizations whose persisted
        ``ndp_user_id`` matches this value are returned. The caller is
        responsible for computing the hash from the authenticated
        user's ``sub`` — the service stays oblivious to identities.

    Returns
    -------
    List[str]
        A list of organization names, filtered by the optional name if
        provided.

    Raises
    ------
    Exception
        If there is an error retrieving the list of organizations.
    """

    # Choose the repository based on 'server'
    if server == "pre_ckan":
        repository = catalog_settings.pre_catalog
    elif server == "global":
        repository = catalog_settings.global_catalog
    else:
        # Default to local if server is 'local' or unrecognized
        repository = catalog_settings.local_catalog

    try:
        if user_hash:
            # We need each org's creator hash to compare, so we have to
            # ask the backend for full org payloads. CKAN needs to be
            # explicitly told to include extras; MongoDB's full-fields
            # mode already returns the top-level ``ndp_user_id``.
            full_orgs = repository.organization_list(
                all_fields=True, include_extras=True
            )
            organizations = [
                org.get("name")
                for org in full_orgs
                if org.get("name") and _extract_ndp_user_id(org) == user_hash
            ]
        else:
            organizations = repository.organization_list(all_fields=False)

        # Filter the organizations if a name is provided
        if name:
            name_lower = name.lower()
            organizations = [org for org in organizations if name_lower in org.lower()]

        return organizations

    except Exception as exc:
        raise Exception(f"Error retrieving list of organizations: {str(exc)}")
