# api/services/datasource_services/search_datasets_by_terms.py

import json
import re
from typing import List, Literal, Optional

import requests.exceptions
from ckanapi import CKANAPIError, NotFound
from fastapi import HTTPException

from api.config.ckan_settings import ckan_settings
from api.models import DataSourceResponse, Resource


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

    if server == "local":
        ckan = ckan_settings.ckan_no_api_key
    elif server == "global":
        ckan = ckan_settings.ckan_global
    elif server == "pre_ckan":
        ckan = ckan_settings.pre_ckan_no_api_key

    escaped_terms = [escape_solr_special_chars(term) for term in terms_list]

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
        datasets = ckan.action.package_search(q=query_string, rows=1000)
        results_list = []

        for dataset in datasets["results"]:
            print(dataset)
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
        # Handle errors when CKAN is unreachable
        if server == "global":
            raise HTTPException(
                status_code=503, detail="Global catalog is not reachable."
            )
        raise HTTPException(
            status_code=503, detail=f"{server.title()} catalog is not reachable."
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
