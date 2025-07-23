# api/routes/update_routes/put_service.py
from typing import Any, Dict, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status

from api.config import ckan_settings
from api.models.update_service_model import ServiceUpdateRequest
from api.services.auth_services import get_current_user
from api.services.service_services import update_service

router = APIRouter()


@router.put(
    "/services/{service_id}",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="Update an existing service",
    description=(
        "Update an existing service in CKAN (full replacement).\n\n"
        "### Path Parameters\n"
        "- **service_id**: The unique identifier of the service to update\n\n"
        "### Optional Fields\n"
        "- **service_name**: Unique name for the service\n"
        "- **service_title**: Display title for the service\n"
        "- **owner_org**: Organization ID (must be 'services')\n"
        "- **service_url**: URL where the service is accessible\n"
        "- **service_type**: Type of service (API, Web Service, etc.)\n"
        "- **notes**: Additional description or notes\n"
        "- **extras**: Additional metadata as key-value pairs\n"
        "- **health_check_url**: URL for service health check endpoint\n"
        "- **documentation_url**: URL to service documentation\n\n"
        "### Query Parameter\n"
        "Use `?server=local` or `?server=pre_ckan` to pick the CKAN instance. "
        "Defaults to 'local' if not provided.\n\n"
        "### Example Payload\n"
        "```json\n"
        "{\n"
        '    "service_name": "updated_auth_api",\n'
        '    "service_title": "Updated User Authentication API",\n'
        '    "service_url": "https://api.example.com/auth/v2",\n'
        '    "service_type": "REST API",\n'
        '    "notes": "Updated API with enhanced security",\n'
        '    "extras": {\n'
        '        "version": "2.2.0",\n'
        '        "environment": "production"\n'
        "    }\n"
        "}\n"
        "```\n"
    ),
    responses={
        200: {
            "description": "Service updated successfully",
            "content": {
                "application/json": {
                    "example": {"message": "Service updated successfully"}
                }
            },
        },
        400: {
            "description": "Bad Request",
            "content": {
                "application/json": {
                    "example": {"detail": "Error updating service: <error message>"}
                }
            },
        },
        404: {
            "description": "Not Found",
            "content": {
                "application/json": {"example": {"detail": "Service not found"}}
            },
        },
    },
)
async def update_service_endpoint(
    service_id: str,
    data: ServiceUpdateRequest,
    server: Literal["local", "pre_ckan"] = Query(
        "local", description="Choose 'local' or 'pre_ckan'. Defaults to 'local'."
    ),
    _: Dict[str, Any] = Depends(get_current_user),
):
    """
    Update a service by service_id (full replacement).

    If ?server=pre_ckan is used, the pre_ckan instance is utilized if enabled
    and valid. Otherwise, defaults to local CKAN.

    Parameters
    ----------
    service_id : str
        The unique identifier of the service to update.
    data : ServiceUpdateRequest
        The updated service information.
    server : Literal['local', 'pre_ckan']
        CKAN instance to use. Defaults to 'local'.
    _ : Dict[str, Any]
        Keycloak user auth (unused).

    Returns
    -------
    dict
        A success message indicating the service was updated.

    Raises
    ------
    HTTPException
        - 400: for update errors or invalid server config
        - 404: if service not found
    """
    try:
        if server == "pre_ckan":
            if not ckan_settings.pre_ckan_enabled:
                raise HTTPException(
                    status_code=400, detail="Pre-CKAN is disabled and cannot be used."
                )
            ckan_instance = ckan_settings.pre_ckan
        else:
            ckan_instance = ckan_settings.ckan

        updated_id = update_service(
            service_id=service_id,
            service_name=data.service_name,
            service_title=data.service_title,
            owner_org=data.owner_org,
            service_url=data.service_url,
            service_type=data.service_type,
            notes=data.notes,
            extras=data.extras,
            health_check_url=data.health_check_url,
            documentation_url=data.documentation_url,
            ckan_instance=ckan_instance,
        )

        if not updated_id:
            raise HTTPException(status_code=404, detail="Service not found")

        return {"message": "Service updated successfully"}

    except HTTPException as he:
        raise he
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Reserved key error: {str(exc)}",
        )
    except Exception as exc:
        error_msg = str(exc)
        if "No scheme supplied" in error_msg:
            raise HTTPException(
                status_code=400,
                detail="Pre-CKAN server is not configured or unreachable.",
            )
        if "not found" in error_msg.lower():
            raise HTTPException(status_code=404, detail="Service not found")
        raise HTTPException(
            status_code=400, detail=f"Error updating service: {error_msg}"
        )