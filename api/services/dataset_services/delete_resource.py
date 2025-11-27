# api/services/dataset_services/delete_resource.py
from api.config.catalog_settings import catalog_settings


def delete_resource(resource_id: str, repository=None):
    """
    Delete a single resource from a dataset.

    This removes only the specified resource, leaving the dataset and
    other resources intact.

    Parameters
    ----------
    resource_id : str
        The ID of the resource to delete
    repository : DataCatalogRepository, optional
        Repository to use. Defaults to local catalog.

    Raises
    ------
    Exception
        If resource not found or deletion fails
    """
    if repository is None:
        repository = catalog_settings.local_catalog

    try:
        repository.resource_delete(id=resource_id)

    except Exception as e:
        error_msg = str(e).lower()
        if "not found" in error_msg:
            raise Exception(f"Resource '{resource_id}' not found.")
        raise Exception(f"Error deleting resource: {str(e)}")
