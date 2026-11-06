# api/routes/status_routes/get.py

from typing import Any, Dict

from fastapi import APIRouter, Depends

from api.services import status_services
from api.services.auth_services import get_current_user
from api.services.status_services import get_full_metrics, get_version_info

router = APIRouter()


@router.get(
    "/",
    response_model=dict,
    summary="Check system status",
    description=("Check if the CKAN and Keycloak servers are active " "and reachable."),
)
async def get_status(
    user_info: Dict[str, Any] = Depends(get_current_user),
):
    """
    Endpoint to check if CKAN and Keycloak are active and reachable.

    Returns
    -------
    str
        A message confirming if CKAN and Keycloak are active.

    Raises
    ------
    HTTPException
        If there is an error connecting to CKAN or Keycloak, an HTTPException
        is raised with a detailed message.
    """
    return_dict = status_services.get_status()

    return return_dict


@router.get(
    "/metrics",
    response_model=dict,
    summary="Retrieve system metrics",
    description="Returns detailed system metrics and service status.",
)
async def get_metrics(
    user_info: Dict[str, Any] = Depends(get_current_user),
):
    """
    Endpoint to retrieve detailed system metrics.

    Returns
    -------
    dict
        System metrics (IP, CPU, memory, disk) and services status.
    """
    return get_full_metrics()


@router.get(
    "/version",
    response_model=dict,
    summary="Installed and latest ep-api version",
    description=(
        "Returns the installed ep-api version and the latest published "
        "release, and whether an update is available, with links to the "
        "release notes and the CHANGELOG. The latest release is read from "
        "RELEASE_CHECK_URL (GitHub by default) and cached; it is null when "
        "it cannot be read or RELEASE_CHECK_ENABLED is false, and then "
        "update_available is null too."
    ),
)
def get_version(
    user_info: Dict[str, Any] = Depends(get_current_user),
):
    """Return the installed version and the latest published release."""
    return get_version_info()
