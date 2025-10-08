# api/services/dataset_services/delete_dataset.py
from api.config.catalog_settings import catalog_settings


def delete_dataset(
    dataset_name: str = None, resource_id: str = None, repository=None
):
    """
    Delete a dataset from catalog by its name or resource_id.

    Uses the configured catalog backend (CKAN or MongoDB) unless a specific
    repository is provided.
    """
    if repository is None:
        repository = catalog_settings.local_catalog

    if not (dataset_name or resource_id):
        raise ValueError("Must provide either dataset_name or resource_id.")

    try:
        # Use the name/id provided to delete
        identifier = dataset_name if dataset_name else resource_id
        repository.package_delete(id=identifier)

    except Exception as e:
        error_msg = str(e).lower()
        if "not found" in error_msg:
            raise Exception(f"Dataset '{identifier}' not found.")
        raise Exception(f"Error deleting dataset: {str(e)}")
