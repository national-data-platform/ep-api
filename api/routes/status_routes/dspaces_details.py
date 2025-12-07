# api/routes/status_routes/dspaces_details.py

from fastapi import APIRouter, HTTPException

from api.config.dspaces_settings import dspaces_settings

router = APIRouter()


@router.get(
    "/dspaces-details",
    summary="Get DataSpaces connection details",
    description=(
        "Returns DataSpaces enabled status and URL for connecting "
        "to the DataSpaces API."
    ),
)
async def get_dspaces_details():
    """
    Endpoint to retrieve DataSpaces connection details.

    Returns
    -------
    dict
        DataSpaces connection details including:
          - dspaces_enabled (bool)
          - dspaces_url (str)

    Raises
    ------
    HTTPException
        If there is an error retrieving DataSpaces details, an HTTPException
        is raised with a 500 status code.
    """
    try:
        return {
            "dspaces_enabled": dspaces_settings.dspaces_enabled,
            "dspaces_url": dspaces_settings.dspaces_url,
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving DataSpaces details: {str(e)}",
        )
