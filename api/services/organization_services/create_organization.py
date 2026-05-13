# api/services/organization_services/create_organization.py
from typing import Any, Dict, Literal, Optional

from ckanapi import NotFound, ValidationError

from api.config import catalog_settings
from api.config.ckan_settings import ckan_settings
from api.services.metadata_services import calculate_md5, hash_user_id


def create_organization(
    name: str,
    title: str,
    description: Optional[str] = None,
    server: Literal["local", "pre_ckan"] = "local",
    user_info: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Create a new organization in CKAN.

    Parameters
    ----------
    name : str
        The name of the organization.
    title : str
        The title of the organization.
    description : Optional[str]
        The description of the organization.
    server : Literal["local", "pre_ckan"]
        The server instance where the organization will be created.
        Defaults to "local".
    user_info : Optional[Dict[str, Any]]
        Authenticated user information. Only used to derive the same
        one-way creator hashes (``ndp_user_id`` and ``ndp_creator_md5``)
        that are already persisted alongside datasets via
        ``inject_ndp_metadata``. The raw user identity is never stored.

    Returns
    -------
    str
        The ID of the created organization.

    Raises
    ------
    Exception
        If there is an error creating the organization.
    """
    # Select repository based on 'server' parameter
    if server == "pre_ckan":
        if not ckan_settings.pre_ckan_enabled:
            raise Exception("Pre-CKAN is disabled and cannot be used.")
        repository = catalog_settings.pre_catalog
    else:
        # Use local catalog (can be CKAN or MongoDB)
        repository = catalog_settings.local_catalog

    create_kwargs: Dict[str, Any] = {
        "name": name,
        "title": title,
        "description": description,
    }
    if user_info:
        create_kwargs["ndp_user_id"] = hash_user_id(user_info)
        create_kwargs["ndp_creator_md5"] = calculate_md5(
            user_info.get("sub", "unknown")
        )

    try:
        organization = repository.organization_create(**create_kwargs)
        # Return the organization ID
        return organization["id"]
    except ValidationError as e:
        raise Exception(f"Validation error: {e.error_dict}")
    except NotFound:
        raise Exception("CKAN API endpoint not found")
    except Exception as e:
        if "Group name already exists in database" in str(e):
            raise Exception("Group name already exists in database")
        raise Exception(f"Error creating organization: {str(e)}")
