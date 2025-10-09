# api/utils/system_metrics.py

import logging

import psutil
import requests

logger = logging.getLogger(__name__)


def get_public_ip():
    """Retrieve the public IP address using external API."""
    try:
        response = requests.get("https://api.ipify.org?format=json")
        response.raise_for_status()
        return response.json().get("ip")
    except requests.RequestException as e:
        return f"Error retrieving IP: {e}"


def get_system_metrics():
    """Get system metrics: CPU percentage, memory and disk in GB."""
    cpu_percent = psutil.cpu_percent(interval=1)

    # Memory in GB
    memory = psutil.virtual_memory()
    memory_used_gb = memory.used / (1024**3)  # Convert bytes to GB
    memory_total_gb = memory.total / (1024**3)

    # Disk in GB
    disk = psutil.disk_usage("/")
    disk_used_gb = disk.used / (1024**3)
    disk_total_gb = disk.total / (1024**3)

    return cpu_percent, memory_used_gb, memory_total_gb, disk_used_gb, disk_total_gb


def get_num_datasets(catalog_repository):
    """
    Count the number of datasets in the catalog backend.

    Parameters
    ----------
    catalog_repository : DataCatalogRepository
        The catalog repository instance to query

    Returns
    -------
    int
        Number of datasets in the catalog, or 0 if error occurs
    """
    try:
        result = catalog_repository.package_search(q="*:*", rows=0)
        return result.get("count", 0)
    except Exception as e:
        logger.error(f"Error counting datasets: {e}")
        return 0


def get_num_services(catalog_repository):
    """
    Count the number of services in the catalog backend.
    Services are stored under the 'services' organization.

    Parameters
    ----------
    catalog_repository : DataCatalogRepository
        The catalog repository instance to query

    Returns
    -------
    int
        Number of services in the catalog, or 0 if error occurs
    """
    try:
        result = catalog_repository.package_search(
            q="*:*", fq="owner_org:services", rows=0
        )
        return result.get("count", 0)
    except Exception as e:
        logger.error(f"Error counting services: {e}")
        return 0


def get_services_titles(catalog_repository):
    """
    Get a list of all service titles from the catalog backend.
    Services are stored under the 'services' organization.

    Parameters
    ----------
    catalog_repository : DataCatalogRepository
        The catalog repository instance to query

    Returns
    -------
    list[str]
        List of service titles, or empty list if error occurs
    """
    try:
        result = catalog_repository.package_search(
            q="*:*", fq="owner_org:services", rows=1000
        )
        return [service.get("title", "") for service in result.get("results", [])]
    except Exception as e:
        logger.error(f"Error getting services titles: {e}")
        return []
