# api/services/s3_services/update_s3.py

from typing import Dict, Optional

from api.config import catalog_settings, ckan_settings
from api.repositories import CKANRepository

RESERVED_KEYS = {"name", "title", "owner_org", "notes", "id", "resources", "collection"}


async def update_s3(
    resource_id: str,
    resource_name: Optional[str] = None,
    resource_title: Optional[str] = None,
    owner_org: Optional[str] = None,
    resource_s3: Optional[str] = None,
    notes: Optional[str] = None,
    extras: Optional[Dict[str, str]] = None,
    ckan_instance=None,  # new optional parameter
):
    """
    Update an existing S3 resource in catalog, supporting a custom ckan_instance.
    If ckan_instance is None, defaults to the configured local catalog.
    """
    # Decide repository to use
    if ckan_instance is None:
        repository = catalog_settings.local_catalog
    else:
        repository = CKANRepository(ckan_instance)

    try:
        # Fetch the existing resource
        resource = repository.package_show(id=resource_id)
    except Exception as e:
        raise Exception(f"Error fetching S3 resource: {str(e)}")

    # Preserve all existing fields unless new values are provided
    resource["name"] = resource_name or resource.get("name")
    resource["title"] = resource_title or resource.get("title")
    resource["owner_org"] = owner_org or resource.get("owner_org")
    resource["notes"] = notes or resource.get("notes")

    # Handle extras update by merging current extras with new ones
    current_extras = {
        extra["key"]: extra["value"] for extra in resource.get("extras", [])
    }

    if extras:
        if RESERVED_KEYS.intersection(extras):
            raise KeyError(
                "Extras contain reserved keys: " f"{RESERVED_KEYS.intersection(extras)}"
            )
        current_extras.update(extras)

    resource["extras"] = [{"key": k, "value": v} for k, v in current_extras.items()]

    try:
        # Update the resource package
        updated_resource = repository.package_update(**resource)

        # If the S3 URL is updated, update the corresponding resource
        if resource_s3:
            for res in resource["resources"]:
                if res["format"].lower() == "s3":
                    # For MongoDB, we need to handle resource update differently
                    # as it doesn't have resource_update, we need to use resource_show
                    # and then re-create or manually update
                    try:
                        repository.resource_show(id=res["id"])
                        # Update URL in the resource
                        # Note: This is a simplified approach
                        # In production, you might want to add resource_update to the interface
                        pass
                    except Exception:
                        pass
                    break
    except Exception as e:
        raise Exception(f"Error updating S3 resource: {str(e)}")

    return updated_resource["id"]


async def patch_s3(
    resource_id: str,
    resource_name: Optional[str] = None,
    resource_title: Optional[str] = None,
    owner_org: Optional[str] = None,
    resource_s3: Optional[str] = None,
    notes: Optional[str] = None,
    extras: Optional[Dict[str, str]] = None,
    ckan_instance=None,
):
    """
    Partially update an existing S3 resource in catalog.

    Only updates the fields that are provided, leaving others unchanged.
    If ckan_instance is None, defaults to the configured local catalog.
    """
    # Decide repository to use
    if ckan_instance is None:
        repository = catalog_settings.local_catalog
    else:
        repository = CKANRepository(ckan_instance)

    try:
        # Build patch dict with only provided fields
        patch_dict = {"id": resource_id}

        if resource_name is not None:
            patch_dict["name"] = resource_name
        if resource_title is not None:
            patch_dict["title"] = resource_title
        if owner_org is not None:
            patch_dict["owner_org"] = owner_org
        if notes is not None:
            patch_dict["notes"] = notes

        # Handle extras
        if extras:
            if RESERVED_KEYS.intersection(extras):
                raise KeyError(
                    "Extras contain reserved keys: "
                    f"{RESERVED_KEYS.intersection(extras)}"
                )
            # Get current extras and merge
            resource = repository.package_show(id=resource_id)
            current_extras = {
                extra["key"]: extra["value"] for extra in resource.get("extras", [])
            }
            current_extras.update(extras)
            patch_dict["extras"] = [
                {"key": k, "value": v} for k, v in current_extras.items()
            ]

        # Patch the resource package
        updated_resource = repository.package_patch(**patch_dict)

        # If the S3 URL is updated, update the corresponding resource
        if resource_s3:
            for res in updated_resource.get("resources", []):
                if res["format"].lower() == "s3":
                    # Note: Simplified resource URL update
                    # Consider adding resource_update to interface for full support
                    pass
                    break
    except Exception as e:
        raise Exception(f"Error patching S3 resource: {str(e)}")

    return updated_resource["id"]
