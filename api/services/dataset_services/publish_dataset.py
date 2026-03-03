# api/services/dataset_services/publish_dataset.py

"""Service for publishing datasets from local catalog to PRE-CKAN."""

import logging
from typing import Any, Dict, List, Optional

from api.config import catalog_settings, ckan_settings
from api.repositories import CKANRepository

logger = logging.getLogger(__name__)

# Fields to exclude when copying dataset to PRE-CKAN
EXCLUDED_FIELDS = {
    "id",
    "revision_id",
    "metadata_created",
    "metadata_modified",
    "creator_user_id",
    "state",
    "type",
    "num_resources",
    "num_tags",
    "relationships_as_subject",
    "relationships_as_object",
    "isopen",
    "organization",
}


def publish_dataset_to_preckan(
    dataset_id: str,
    user_info: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Publish a dataset from local catalog to PRE-CKAN.

    This function fetches a dataset from the local catalog and creates
    a copy in PRE-CKAN with the same metadata and resources.

    Parameters
    ----------
    dataset_id : str
        The ID or name of the dataset to publish.
    user_info : Optional[Dict[str, Any]]
        User information for authorization.

    Returns
    -------
    str
        The ID of the newly created dataset in PRE-CKAN.

    Raises
    ------
    ValueError
        If PRE-CKAN is not enabled or dataset not found.
    Exception
        For errors during dataset creation.
    """
    # Check if PRE-CKAN is enabled
    if not ckan_settings.pre_ckan_enabled:
        raise ValueError("PRE-CKAN is disabled and cannot be used.")

    # Get local repository
    local_repository = catalog_settings.local_catalog

    # Get PRE-CKAN repository
    preckan_repository = CKANRepository(ckan_settings.pre_ckan)

    # Fetch dataset from local catalog
    try:
        dataset = local_repository.package_show(id=dataset_id)
    except Exception as exc:
        raise ValueError(f"Dataset not found in local catalog: {str(exc)}")

    # Prepare dataset dict for PRE-CKAN (exclude system fields)
    dataset_dict = {
        key: value
        for key, value in dataset.items()
        if key not in EXCLUDED_FIELDS and value is not None
    }

    # Override owner_org with PRE-CKAN organization if configured
    if ckan_settings.pre_ckan_organization:
        original_org = dataset_dict.get("owner_org", "none")
        dataset_dict["owner_org"] = ckan_settings.pre_ckan_organization
        logger.info(
            f"Using PRE-CKAN organization '{ckan_settings.pre_ckan_organization}' "
            f"(original: '{original_org}')"
        )
    else:
        # Resolve owner_org: if it's a UUID, get the org name from local catalog
        owner_org = dataset_dict.get("owner_org")
        if owner_org:
            try:
                org = local_repository.organization_show(id=owner_org)
                # Use org name instead of UUID for PRE-CKAN compatibility
                dataset_dict["owner_org"] = org.get("name", owner_org)
                logger.info(f"Resolved owner_org '{owner_org}' to '{dataset_dict['owner_org']}'")
            except Exception:
                # If we can't resolve, keep original value
                logger.warning(f"Could not resolve owner_org '{owner_org}', using as-is")

    # Extract resources to create separately
    resources = dataset_dict.pop("resources", [])

    # Clean up resources (remove system fields)
    cleaned_resources = []
    for resource in resources:
        cleaned_resource = {
            key: value
            for key, value in resource.items()
            if key
            not in {
                "id",
                "package_id",
                "revision_id",
                "created",
                "metadata_modified",
                "state",
                "position",
                "datastore_active",
                "url_type",
                "hash",
                "size",
                "cache_url",
                "cache_last_updated",
                "last_modified",
            }
            and value is not None
        }
        cleaned_resources.append(cleaned_resource)

    # Create dataset in PRE-CKAN
    try:
        new_dataset = preckan_repository.package_create(**dataset_dict)
        new_dataset_id = new_dataset["id"]
        logger.info(f"Dataset created in PRE-CKAN with ID: {new_dataset_id}")
    except Exception as exc:
        error_msg = str(exc)
        if "That name is already in use" in error_msg:
            raise ValueError(
                f"A dataset with name '{dataset_dict.get('name')}' "
                "already exists in PRE-CKAN."
            )
        if "Organization does not exist" in error_msg:
            raise ValueError(
                f"Organization '{dataset_dict.get('owner_org')}' "
                "does not exist in PRE-CKAN. Create it first."
            )
        raise Exception(f"Error creating dataset in PRE-CKAN: {error_msg}")

    # Create resources in PRE-CKAN
    for resource in cleaned_resources:
        try:
            resource["package_id"] = new_dataset_id
            preckan_repository.resource_create(**resource)
            logger.info(
                f"Resource '{resource.get('name', 'unnamed')}' "
                f"created in PRE-CKAN dataset {new_dataset_id}"
            )
        except Exception as exc:
            logger.warning(
                f"Failed to create resource in PRE-CKAN: {str(exc)}. "
                "Continuing with remaining resources."
            )

    return new_dataset_id
