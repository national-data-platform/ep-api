# api/services/organization_services/delete_organization.py
from api.config import catalog_settings


def delete_organization(organization_name: str, repository=None, cascade: bool = True):
    """
    Delete an organization from catalog by its name.

    Uses the configured catalog backend (CKAN or MongoDB) unless a specific
    repository is provided.

    Parameters
    ----------
    organization_name : str
        Organization name to delete.
    repository : optional
        Backend repository to act on. Falls back to the configured local
        catalog.
    cascade : bool
        When True (default, legacy behavior), also delete every dataset
        owned by the organization before removing the organization. When
        False, refuse to delete an organization that still has datasets
        inside — the caller can clean them up first and retry. This
        narrower mode is what the UI uses, so users do not lose data by
        clicking "Delete" on an organization card.
    """
    if repository is None:
        repository = catalog_settings.local_catalog

    try:
        # Retrieve the organization to ensure it exists
        organization = repository.organization_show(id=organization_name)
        organization_id = organization["id"]

        # Inspect datasets owned by the org so we can either delete them
        # (cascade) or refuse the call (no cascade).
        datasets = repository.package_search(
            fq=f"owner_org:{organization_id}", rows=1000
        )
        dataset_results = datasets.get("results", []) or []

        if not cascade and dataset_results:
            raise Exception(
                f"Organization still has {len(dataset_results)} dataset(s) "
                "inside; delete them first or call with cascade=true"
            )

        if cascade:
            for dataset in dataset_results:
                # Use package_delete for repository pattern
                repository.package_delete(id=dataset["id"])

        # Delete the organization
        repository.organization_delete(id=organization_id)
        # Note: MongoDB doesn't have separate purge operation, it's handled in delete
        # For CKAN, we may need to call purge separately
        try:
            repository.organization_purge(id=organization_id)
        except AttributeError:
            # MongoDB doesn't have purge method, that's fine
            pass

    except Exception as e:
        error_msg = str(e).lower()
        if "not found" in error_msg:
            raise Exception("Organization not found")
        if "still has" in error_msg and "dataset" in error_msg:
            # Surface the dataset-count message untouched so the route
            # and the UI can recognize it for a friendly error.
            raise
        raise Exception(f"Error deleting organization: {str(e)}")
