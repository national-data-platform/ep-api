# api/services/datasource_services/search_datasets_by_terms.py

import json
import re
from typing import List, Literal, Optional

import requests.exceptions
from ckanapi import CKANAPIError, NotFound
from fastapi import HTTPException

from api.config.catalog_settings import catalog_settings
from api.models import DataSourceResponse, Resource

# Results are asked for a page at a time, never more than the catalog can
# serve before its gateway gives up (issue #402), and no more datasets are
# looked at than the single 1000-row request used to return.
PAGE_SIZE = 100
MAX_DATASETS = 1000


def solr_phrase(value: str) -> str:
    """
    Quote a search term as a Solr phrase.

    CKAN's text field splits words at letter/digit boundaries, so an unquoted
    ``macav2`` matches every dataset containing ``macav`` or ``2`` (4224 on the
    global catalog). As a phrase it matches only those parts next to each
    other, which is what the search is for.

    Parameters
    ----------
    value : str
        The search term.

    Returns
    -------
    str
        The term between double quotes, with inner quotes and backslashes
        escaped.
    """
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def escape_solr_special_chars(value: str) -> str:
    """
    Escape special characters in Solr queries.

    Parameters
    ----------
    value : str
        The string value to escape.

    Returns
    -------
    str
        The escaped string with Solr special characters escaped.
    """
    pattern = re.compile(r'([+\-\!\(\)\{\}\[\]\^"~\*\?:\\])')
    return pattern.sub(r"\\\1", value)


async def search_datasets_by_terms(
    terms_list: List[str],
    keys_list: Optional[List[Optional[str]]] = None,
    server: Literal["local", "global", "pre_ckan"] = "global",
) -> List[DataSourceResponse]:
    """
    Search datasets by terms with improved error handling for service
    unavailability.

    Parameters
    ----------
    terms_list : List[str]
        List of search terms to look for in datasets.
    keys_list : Optional[List[Optional[str]]], optional
        List of keys corresponding to each term for field-specific search.
        Use None for global search of a term.
    server : Literal["local", "global", "pre_ckan"], optional
        The CKAN server to search on. Defaults to "global".

    Returns
    -------
    List[DataSourceResponse]
        List of datasets that match the search criteria.

    Raises
    ------
    HTTPException
        400: Invalid server specified
        503: CKAN service unavailable
        504: Request timeout
    """
    if server not in ["local", "global", "pre_ckan"]:
        raise HTTPException(
            status_code=400,
            detail=(
                "Invalid server specified. Use 'local', " "'global', or 'pre_ckan'."
            ),
        )

    # Get the appropriate repository based on server selection
    if server == "local":
        repository = catalog_settings.local_catalog
    elif server == "global":
        repository = catalog_settings.global_catalog
    elif server == "pre_ckan":
        repository = catalog_settings.pre_catalog

    escaped_terms = [solr_phrase(term) for term in terms_list]

    query_parts = []

    if keys_list:
        processed_keys = [
            None if key is None or key.lower() == "null" else key for key in keys_list
        ]

        for term, key in zip(escaped_terms, processed_keys):
            if key:
                escaped_key = escape_solr_special_chars(key)
                query_parts.append(f"{escaped_key}:{term}")
            else:
                query_parts.append(term)
    else:
        query_parts = escaped_terms

    query_string = " AND ".join(query_parts)

    try:
        results_list = []

        for dataset in _search_pages(repository, query_string):
            dataset_str = json.dumps(dataset).lower()

            if all(term.lower() in dataset_str for term in terms_list):
                resources_list = [
                    Resource(
                        id=res["id"],
                        url=res["url"],
                        name=res["name"],
                        description=res.get("description"),
                        format=res.get("format"),
                    )
                    for res in dataset.get("resources", [])
                ]

                organization_name = (
                    dataset.get("organization", {}).get("name")
                    if dataset.get("organization")
                    else None
                )

                extras = {
                    extra["key"]: extra["value"] for extra in dataset.get("extras", [])
                }

                if "mapping" in extras:
                    try:
                        extras["mapping"] = json.loads(extras["mapping"])
                    except json.JSONDecodeError:
                        pass

                if "processing" in extras:
                    try:
                        extras["processing"] = json.loads(extras["processing"])
                    except json.JSONDecodeError:
                        pass

                results_list.append(
                    DataSourceResponse(
                        id=dataset["id"],
                        name=dataset["name"],
                        title=dataset["title"],
                        owner_org=organization_name,
                        description=dataset.get("notes"),
                        resources=resources_list,
                        extras=extras,
                    )
                )

        return results_list

    except NotFound:
        return []

    except CKANAPIError as _:  # noqa: F841
        # The catalog answered, with an error: a gateway timeout from its
        # proxy arrives here too. It is not unreachable (issue #402).
        name = "Global" if server == "global" else server.title()
        raise HTTPException(
            status_code=503,
            detail=(
                f"{name} catalog could not answer this search: it returned an "
                "error or timed out. Try again, or with more specific terms."
            ),
        )

    except requests.exceptions.ConnectionError:
        # Handle connection errors with user-friendly messages
        if server == "local":
            raise HTTPException(
                status_code=503,
                detail=(
                    "Local CKAN catalog is currently unavailable. "
                    "Please check if the service is running."
                ),
            )
        elif server == "global":
            raise HTTPException(
                status_code=503,
                detail=(
                    "Global catalog is currently unavailable. "
                    "Please try again later."
                ),
            )
        elif server == "pre_ckan":
            raise HTTPException(
                status_code=503,
                detail=(
                    "Pre-CKAN catalog is currently unavailable. "
                    "Please check the configuration."
                ),
            )

    except requests.exceptions.Timeout:
        # Handle timeout errors
        raise HTTPException(
            status_code=504,
            detail=(
                f"Request to {server} catalog timed out. " "Please try again later."
            ),
        )

    except Exception as e:
        # Handle any connection-related errors in the error message
        error_str = str(e)

        # Check if the error is connection-related
        if any(
            keyword in error_str.lower()
            for keyword in [
                "connection",
                "timeout",
                "refused",
                "unreachable",
                "network",
                "max retries exceeded",
                "connection pool",
                "connect timeout",
            ]
        ):
            if server == "local":
                raise HTTPException(
                    status_code=503,
                    detail=(
                        "Local CKAN catalog is currently unavailable. "
                        "Please check if the service is running."
                    ),
                )
            elif server == "global":
                raise HTTPException(
                    status_code=503,
                    detail=(
                        "Global catalog is currently unavailable. "
                        "Please try again later."
                    ),
                )
            elif server == "pre_ckan":
                raise HTTPException(
                    status_code=503,
                    detail=(
                        "Pre-CKAN catalog is currently unavailable. "
                        "Please check the configuration."
                    ),
                )

        # For non-connection errors, return a generic error message
        # without exposing internal details
        raise HTTPException(
            status_code=400, detail="Error searching for datasets. Please try again."
        )


def _search_pages(repository, query_string: str):
    """
    Yield the datasets matching a query, one page of results at a time.

    Parameters
    ----------
    repository : DataCatalogRepository
        The catalog to search.
    query_string : str
        The query for ``package_search``.

    Yields
    ------
    dict
        Each dataset, until the catalog has no more or ``MAX_DATASETS`` have
        been returned.
    """
    start = 0
    while start < MAX_DATASETS:
        page = repository.package_search(q=query_string, rows=PAGE_SIZE, start=start)
        results = page.get("results", [])
        yield from results
        start += len(results)
        count = page.get("count")
        if len(results) < PAGE_SIZE or (count is not None and start >= count):
            return
