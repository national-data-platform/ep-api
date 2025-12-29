# api/routes/status_routes/get_jupyter.py

from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException

from api.config.swagger_settings import swagger_settings
from api.services.auth_services import get_current_user

router = APIRouter()


@router.get(
    "/jupyter",
    summary="Get jupyter connection details",
    description=("Returns the URL where the JupyterHub is available."),
)
async def get_jupyter_details(
    user_info: Dict[str, Any] = Depends(get_current_user),
):
    """
    Endpoint to retrieve jupyter connection details.

    Returns
    -------
    dict
        A dictionary containing the Jupyter URL.

    Raises
    ------
    HTTPException
        If there is an error retrieving Kafka details, an HTTPException
        is raised with a 500 status code.
    """
    try:
        return {"jupyter_url": swagger_settings.jupyter_url}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error retrieving Kafka details: {str(e)}"
        )
