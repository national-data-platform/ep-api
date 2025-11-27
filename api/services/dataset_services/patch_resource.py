# api/services/dataset_services/patch_resource.py
from typing import Any, Dict, Optional

from api.config.catalog_settings import catalog_settings


def patch_resource(
    resource_id: str,
    name: Optional[str] = None,
    url: Optional[str] = None,
    description: Optional[str] = None,
    format: Optional[str] = None,
    repository=None,
) -> Dict[str, Any]:
    """
    Partially update a resource (only specified fields).

    This updates only the fields that are provided, leaving other
    fields unchanged.

    Parameters
    ----------
    resource_id : str
        The ID of the resource to patch
    name : str, optional
        New resource name
    url : str, optional
        New resource URL
    description : str, optional
        New resource description
    format : str, optional
        New resource format
    repository : DataCatalogRepository, optional
        Repository to use. Defaults to local catalog.

    Returns
    -------
    dict
        Updated resource data

    Raises
    ------
    Exception
        If resource not found or patch fails
    """
    if repository is None:
        repository = catalog_settings.local_catalog

    # Build patch data with only provided fields
    patch_data = {"id": resource_id}
    if name is not None:
        patch_data["name"] = name
    if url is not None:
        patch_data["url"] = url
    if description is not None:
        patch_data["description"] = description
    if format is not None:
        patch_data["format"] = format

    try:
        return repository.resource_patch(**patch_data)

    except Exception as e:
        error_msg = str(e).lower()
        if "not found" in error_msg:
            raise Exception(f"Resource '{resource_id}' not found.")
        raise Exception(f"Error patching resource: {str(e)}")
