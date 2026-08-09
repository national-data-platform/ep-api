# api/services/service_services/redirect_service.py

from typing import Any, Dict, Optional, Tuple

from api.services.datasource_services.search_datasource import search_datasource

# The extra a service sets to be reached only by callers the Endpoint can
# authenticate. Absent means open, which is how every service registered so
# far behaves and must keep behaving.
REQUIRES_AUTH_EXTRA = "requires_auth"

_TRUTHY = {"true", "1", "yes", "on"}


def _requires_auth(extras: Optional[Dict[str, Any]]) -> bool:
    """
    Whether a service asks the Endpoint to authenticate callers first.

    Extras arrive as strings from CKAN and as whatever was posted from
    MongoDB, so a real boolean and the usual spellings are both accepted.
    Anything else — including the extra being absent — means open.
    """
    if not extras:
        return False

    value = extras.get(REQUIRES_AUTH_EXTRA)
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in _TRUTHY


async def get_service_access(
    service_identifier: str, server: str = "local"
) -> Tuple[Optional[str], bool, Optional[str]]:
    """
    Get a service's URL and whether reaching it requires authentication.

    One catalog search answers both: the URL the proxy forwards to, and the
    ``requires_auth`` extra the Endpoint checks before forwarding anything.

    Parameters
    ----------
    service_identifier : str
        Service name to search for.
    server : str
        Catalog to search on ('local', 'global', 'pre_ckan').

    Returns
    -------
    Tuple[Optional[str], bool, Optional[str]]
        (service_url, requires_auth, error_message). On success the error is
        None; on failure the URL is None, ``requires_auth`` is False and
        unused, and the message says why.
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
            return None, False, f"Service '{service_identifier}' not found"

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
            return None, False, f"Service URL not found for '{service_identifier}'"

        return service_url, _requires_auth(service_dataset.extras), None

    except Exception as exc:
        error_msg = str(exc)
        if "No scheme supplied" in error_msg:
            return None, False, "Server is not configured or unreachable."
        return None, False, f"Error retrieving service: {error_msg}"


async def get_service_url(
    service_identifier: str, server: str = "local"
) -> Tuple[Optional[str], Optional[str]]:
    """
    Get service URL by service name.

    Kept for callers that only need the URL; the access rule comes from
    ``get_service_access``, which this delegates to.

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
    service_url, _, error = await get_service_access(service_identifier, server=server)
    return service_url, error
