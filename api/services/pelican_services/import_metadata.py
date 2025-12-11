# api/services/pelican_services/import_metadata.py
"""
Service for importing Pelican file metadata into local catalog.
"""

from typing import Dict, Any
from api.repositories.pelican_repository import PelicanRepository
from api.config.catalog_settings import catalog_settings
import logging
import os

logger = logging.getLogger(__name__)


def import_file_as_resource(
    pelican_repo: PelicanRepository,
    pelican_url: str,
    package_id: str,
    resource_name: str = None,
    resource_description: str = None
) -> Dict[str, Any]:
    """
    Import a Pelican file as a resource in the local catalog.

    Parameters
    ----------
    pelican_repo : PelicanRepository
        Initialized Pelican repository
    pelican_url : str
        Full pelican:// URL to the file
    package_id : str
        Package ID to add this resource to
    resource_name : str, optional
        Resource name (defaults to filename)
    resource_description : str, optional
        Resource description

    Returns
    -------
    dict
        Created resource data

    Raises
    ------
    Exception
        If import fails
    """
    try:
        # Extract path from pelican:// URL
        # Format: pelican://federation/path/to/file
        if not pelican_url.startswith("pelican://"):
            raise ValueError("URL must start with pelican://")

        path = pelican_url.replace("pelican://", "").split("/", 1)[1]
        path = "/" + path  # Pelican paths need leading /

        # Get file info
        file_info = pelican_repo.file_info(path)

        # Default resource name to filename
        if resource_name is None:
            resource_name = os.path.basename(path)

        # Create resource in local catalog
        repository = catalog_settings.local_catalog
        resource_data = {
            "package_id": package_id,
            "name": resource_name,
            "url": pelican_url,  # Store original pelican:// URL
            "description": resource_description or f"Pelican federated file: {path}",
            "format": "pelican",
            "size": file_info.get("size", 0)
        }

        created_resource = repository.resource_create(**resource_data)
        logger.info(f"Imported Pelican file as resource: {pelican_url}")

        return {
            "success": True,
            "resource": created_resource
        }

    except Exception as e:
        logger.error(f"Error importing Pelican file {pelican_url}: {e}")
        return {
            "success": False,
            "error": str(e)
        }
