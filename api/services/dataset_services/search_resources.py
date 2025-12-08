# api/services/dataset_services/search_resources.py
from typing import Any, Dict, Optional

from api.config.catalog_settings import catalog_settings


def search_resources(
    query: Optional[str] = None,
    name: Optional[str] = None,
    url: Optional[str] = None,
    format: Optional[str] = None,
    description: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    repository=None,
) -> Dict[str, Any]:
    """
    Search for resources matching the given criteria.

    Parameters
    ----------
    query : str, optional
        General search query (searches name, url, description)
    name : str, optional
        Filter by resource name (partial match)
    url : str, optional
        Filter by resource URL (partial match)
    format : str, optional
        Filter by resource format (exact match, case-insensitive)
    description : str, optional
        Filter by description (partial match)
    limit : int
        Maximum number of results to return
    offset : int
        Number of results to skip for pagination
    repository : DataCatalogRepository, optional
        Repository to use. Defaults to local catalog.

    Returns
    -------
    dict
        Search results with 'count' and 'results' keys
    """
    if repository is None:
        repository = catalog_settings.local_catalog

    try:
        return repository.resource_search(
            query=query,
            name=name,
            url=url,
            format=format,
            description=description,
            limit=limit,
            offset=offset,
        )

    except Exception as e:
        raise Exception(f"Error searching resources: {str(e)}")
