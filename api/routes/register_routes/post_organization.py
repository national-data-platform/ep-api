# api/routes/register_routes/post_organization.py
from typing import Any, Dict, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status

from api.models import OrganizationRequest
from api.services import organization_services
from api.services.auth_services import get_current_user

router = APIRouter()


@router.post(
    "/organization",
    response_model=dict,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new organization",
    description=(
        "Create a new organization with the given name, title, " "and description."
    ),
    responses={
        201: {
            "description": "Organization created successfully",
            "content": {
                "application/json": {
                    "example": {
                        "id": "305284e6-6338-4e13-b39b-e6efe9f1c45a",
                        "message": "Organization created successfully",
                    }
                }
            },
        },
        400: {
            "description": "Bad Request",
            "content": {
                "application/json": {
                    "example": {"detail": "Organization name already exists."}
                }
            },
        },
    },
)
async def create_organization_endpoint(
    org: OrganizationRequest,
    server: Literal["local", "pre_ckan"] = Query(
        "local", description="Specify 'local' or 'pre_ckan'. Defaults to 'local'."
    ),
    _: Dict[str, Any] = Depends(get_current_user),
):
    """
    Endpoint to create a new organization in CKAN.

    Parameters
    ----------
    org : OrganizationRequest
        An object containing the name, title, and description of
        the organization.
    server : Literal['local', 'pre_ckan']
        The CKAN server instance to use.

    Returns
    -------
    dict
        A dictionary containing the ID of the created organization
        and a success message.

    Raises
    ------
    HTTPException
        If there is an error creating the organization, an
        HTTPException is raised with a detailed message.
    """
    try:
        organization_id = organization_services.create_organization(
            name=org.name, title=org.title, description=org.description, server=server
        )
        return {
            "id": organization_id,
            "message": "Organization created successfully",
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
