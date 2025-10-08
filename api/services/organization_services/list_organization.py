# api/services/organization_services/list_organization.py
from typing import List, Optional

from api.config import catalog_settings


def list_organization(name: Optional[str] = None, server: str = "global") -> List[str]:
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
        organizations = repository.organization_list(all_fields=False)

        # Filter the organizations if a name is provided
        if name:
            name_lower = name.lower()
            organizations = [org for org in organizations if name_lower in org.lower()]

        return organizations

    except Exception as exc:
        raise Exception(f"Error retrieving list of organizations: {str(exc)}")
