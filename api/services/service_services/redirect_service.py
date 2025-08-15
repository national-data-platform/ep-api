# api/services/service_services/redirect_service.py

from typing import Optional, Tuple

from api.services.datasource_services.search_datasource import search_datasource


async def get_service_url(
    service_identifier: str, server: str = "local"
) -> Tuple[Optional[str], Optional[str]]:
    """
    Get service URL by service name.

    Parameters
    ----------
    service_identifier : str
        Service name to search for.
    server : str
        CKAN server to search on ('local', 'global', 'pre_ckan').

    Returns
    -------
    Tuple[Optional[str], Optional[str]]
        Tuple of (service_url, error_message). If successful, returns
        (url, None). If failed, returns (None, error_message).
    """
    try:
        # Search for service by name in the 'services' organization
        search_results = await search_datasource(
            dataset_name=service_identifier,
            owner_org="services",
            server=server,
        )

        # If no results found, return error
        if not search_results:
            return None, f"Service '{service_identifier}' not found"

        # Get the first matching service (names should be unique)
        service_dataset = search_results[0]

        # Extract service URL from resources
        service_url = None
        for resource in service_dataset.resources:
            if resource.format and resource.format.lower() == "service":
                service_url = resource.url
                break

        # If no service resource found, try to get from extras
        if service_url is None and service_dataset.extras:
            service_url = service_dataset.extras.get("service_url")

        # If still no URL found, return error
        if service_url is None:
            return None, f"Service URL not found for '{service_identifier}'"

        return service_url, None

    except Exception as exc:
        error_msg = str(exc)
        if "No scheme supplied" in error_msg:
            return None, "Server is not configured or unreachable."
        return None, f"Error retrieving service: {error_msg}"
