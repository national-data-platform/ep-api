# api/services/url_services/add_url.py
import json
from typing import Any, Dict, Optional

from api.config import catalog_settings, ckan_settings
from api.repositories import CKANRepository
from api.services.metadata_services import inject_ndp_metadata

RESERVED_KEYS = {
    "name",
    "title",
    "owner_org",
    "notes",
    "id",
    "resources",
    "collection",
    "url",
    "mapping",
    "processing",
    "file_type",
}


def add_url(
    resource_name,
    resource_title,
    owner_org,
    resource_url,
    file_type="",
    notes="",
    extras=None,
    mapping=None,
    processing=None,
    ckan_instance=None,
    user_info: Optional[Dict[str, Any]] = None,
):
    """
    Add a URL resource to CKAN.

    Parameters
    ----------
    resource_name : str
        The name of the resource to be created.
    resource_title : str
        The title of the resource to be created.
    owner_org : str
        The ID of the organization to which the resource belongs.
    resource_url : str
        The URL of the resource to be added.
    file_type : str, optional
        The type of the file (e.g. 'stream', 'CSV', 'TXT', 'JSON', 'NetCDF').
    notes : str, optional
        Additional notes about the resource (default is an empty string).
    extras : dict, optional
        Additional metadata to be added to the resource package as extras
        (default is None).
    mapping : dict, optional
        Mapping information for the dataset (default is None).
    processing : dict, optional
        Processing information for the dataset based on the file type
        (default is None).
    ckan_instance : optional
        A CKAN instance to use for resource creation. If not provided,
        uses the default `ckan_settings.ckan`.
    user_info : Optional[Dict[str, Any]]
        User information for NDP metadata injection.

    Returns
    -------
    str
        The ID of the created resource if successful.

    Raises
    ------
    ValueError, KeyError, Exception
        If there is any error in validation or creation.
    """

    if not isinstance(extras, (dict, type(None))):
        raise ValueError("Extras must be a dictionary or None.")

    if extras and RESERVED_KEYS.intersection(extras):
        raise KeyError(
            "Extras contain reserved keys: " f"{RESERVED_KEYS.intersection(extras)}"
        )

    # Decide repository to use
    if ckan_instance is None:
        repository = catalog_settings.local_catalog
    else:
        repository = CKANRepository(ckan_instance)

    url_extras = {"file_type": file_type}

    if mapping:
        url_extras["mapping"] = json.dumps(mapping)
    if processing:
        url_extras["processing"] = json.dumps(processing)

    extras_cleaned = extras.copy() if extras else {}
    extras_cleaned.update(url_extras)

    # Inject NDP metadata if user_info is provided
    if user_info:
        extras_cleaned = inject_ndp_metadata(user_info, extras_cleaned)

    try:
        resource_package_dict = {
            "name": resource_name,
            "title": resource_title,
            "owner_org": owner_org,
            "notes": notes,
            "extras": [{"key": k, "value": v} for k, v in extras_cleaned.items()],
        }

        resource_package = repository.package_create(**resource_package_dict)
        resource_package_id = resource_package["id"]

    except Exception as e:
        raise Exception(f"Error creating resource package: {str(e)}")

    if resource_package_id:
        try:
            repository.resource_create(
                package_id=resource_package_id,
                url=resource_url,
                name=resource_name,
                description=f"Resource pointing to {resource_url}",
                format="url",
            )
        except Exception as e:
            raise Exception(f"Error creating resource: {str(e)}")

        return resource_package_id
    else:
        raise Exception("Unknown error occurred")
