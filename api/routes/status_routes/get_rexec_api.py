# api/routes/status_routes/get_rexec_api.py

from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException

from api.config.rexec_settings import rexec_settings
from api.services.auth_services import get_user_for_write_operation

router = APIRouter()


@router.get(
    "/rexec",
    summary="Get rexec deployment api connection details",
    description=("Returns the the URL where the Remote Execution Deployment API is available."),
)
async def get_rexec_details(
    _: Dict[str, Any] = Depends(get_user_for_write_operation)
):
    """
    Endpoint to retrieve rexec deployment api connection details.

    Returns
    -------
    dict
        A dictionary containing the Rexec deployment API URL.

    Raises
    ------
    HTTPException
        If there is an error retrieving Rexec details, an HTTPException
        is raised with a 500 status code.
    """
    try:
        return {"deployment_api_url": rexec_settings.deployment_api_url}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error retrieving Rexec deployment API details: {str(e)}"
        )
