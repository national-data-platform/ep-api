# api/services/dataset_services/get_resource.py
from typing import Any, Dict

from api.config.catalog_settings import catalog_settings


def get_resource(resource_id: str, repository=None) -> Dict[str, Any]:
    """
    Get a resource by its ID.

    Parameters
    ----------
    resource_id : str
        The ID of the resource to retrieve
    repository : DataCatalogRepository, optional
        Repository to use. Defaults to local catalog.

    Returns
    -------
    dict
        Resource data

    Raises
    ------
    Exception
        If resource not found
    """
    if repository is None:
        repository = catalog_settings.local_catalog

    try:
        return repository.resource_show(id=resource_id)

    except Exception as e:
        error_msg = str(e).lower()
        if "not found" in error_msg:
            raise Exception(f"Resource '{resource_id}' not found.")
        raise Exception(f"Error retrieving resource: {str(e)}")
