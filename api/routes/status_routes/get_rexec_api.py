# api\routes\status_routes\get_rexec_api.py

from fastapi import APIRouter, HTTPException

from api.config.rexec_settings import rexec_settings

router = APIRouter()


@router.get(
    "/rexec",
    summary="Get rexec deployment api connection details",
    description=("Returns the the URL where the Remote Execution Deployment API is available."),
)
async def get_rexec_details():
    """
    Endpoint to retrieve rexec deployment api connection details.

    Returns
    -------
    dict
        A dictionary containing the Rexec deployment API URL.

    Raises
    ------
    HTTPException
        If there is an error retrieving Kafka details, an HTTPException
        is raised with a 500 status code.
    """
    try:
        return {"deployment_api_url": rexec_settings.deployment_api_url}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error retrieving Rexec deployment API details: {str(e)}"
        )
