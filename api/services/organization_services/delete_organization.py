# api/services/organization_services/delete_organization.py
from api.config import catalog_settings


def delete_organization(organization_name: str, repository=None):
    """
    Delete an organization from catalog by its name.

    Uses the configured catalog backend (CKAN or MongoDB) unless a specific
    repository is provided.
    """
    if repository is None:
        repository = catalog_settings.local_catalog

    try:
        # Retrieve the organization to ensure it exists
        organization = repository.organization_show(id=organization_name)
        organization_id = organization["id"]

        # Delete all datasets associated with the organization
        datasets = repository.package_search(
            fq=f"owner_org:{organization_id}", rows=1000
        )
        for dataset in datasets["results"]:
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
        raise Exception(f"Error deleting organization: {str(e)}")
