# api/routes/update_routes/patch_service.py
from typing import Any, Dict, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status

from api.config import ckan_settings
from api.models.update_service_model import ServiceUpdateRequest
from api.services.auth_services import get_user_for_write_operation
from api.services.service_services import patch_service

router = APIRouter()


@router.patch(
    "/services/{service_id}",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="Partially update an existing service",
    description=(
        "Partially update an existing service in CKAN.\n\n"
        "Only updates the fields that are provided, leaving others "
        "unchanged. This is useful when you only want to modify specific "
        "attributes without affecting the rest of the service.\n\n"
        "### Path Parameters\n"
        "- **service_id**: The unique identifier of the service to update\n\n"
        "### Optional Fields (only provide fields to update)\n"
        "- **service_name**: Unique name for the service (lowercase, no spaces)\n"
        "- **service_title**: Human-readable display title for the service\n"
        "- **owner_org**: Organization ID that owns this service\n"
        "- **service_url**: URL endpoint where the service is accessible\n"
        "- **service_type**: Type classification of the service (API, Web Service, Microservice, etc.)\n"
        "- **notes**: Description or additional notes about the service\n"
        "- **extras**: Additional metadata (will be merged with existing)\n"
        "- **health_check_url**: URL endpoint for service health monitoring\n"
        "- **documentation_url**: URL to service documentation or API docs\n\n"
        "### Query Parameter\n"
        "Use `?server=local` or `?server=pre_ckan` to pick the CKAN instance. "
        "Defaults to 'local' if not provided.\n\n"
        "### Authorization\n"
        "This endpoint requires authentication. If organization-based "
        "access control is enabled, only users belonging to the configured "
        "organization can update services.\n\n"
        "### Example Payload (partial update)\n"
        "```json\n"
        "{\n"
        '    "service_url": "https://api.example.com/auth/v2.1",\n'
        '    "service_type": "REST API",\n'
        '    "health_check_url": "https://api.example.com/health",\n'
        '    "extras": {\n'
        '        "version": "2.1.0",\n'
        '        "last_updated": "2024-01-15",\n'
        '        "environment": "production",\n'
        '        "maintainer": "platform-team@example.com"\n'
        "    }\n"
        "}\n"
        "```\n"
        "Note: Only `service_url`, `service_type`, `health_check_url` and `extras` "
        "will be updated. All other fields remain unchanged, and the new extras "
        "will be merged with existing ones.\n"
    ),
    responses={
        200: {
            "description": "Service partially updated successfully",
            "content": {
                "application/json": {
                    "example": {"message": "Service updated successfully"}
                }
            },
        },
        401: {
            "description": "Unauthorized - Authentication required",
            "content": {
                "application/json": {"example": {"detail": "Invalid or expired token"}}
            },
        },
        403: {
            "description": "Forbidden - Organization membership required",
            "content": {
                "application/json": {
                    "example": {
                        "detail": (
                            "Access forbidden: write operations require "
                            "membership in organization 'Research Group'"
                        )
                    }
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
async def patch_service_endpoint(
    service_id: str,
    data: ServiceUpdateRequest,
    server: Literal["local", "pre_ckan"] = Query(
        "local", description="Choose 'local' or 'pre_ckan'. Defaults to 'local'."
    ),
    _: Dict[str, Any] = Depends(get_user_for_write_operation),
):
    """
    Partially update a service by service_id.

    Only updates the fields that are provided in the request, leaving all
    other fields unchanged. This is ideal for making small updates without
    needing to provide the complete service information.

    Parameters
    ----------
    service_id : str
        The unique identifier of the service to patch.
    data : ServiceUpdateRequest
        The partial service update information.
    server : Literal['local', 'pre_ckan']
        CKAN instance to use. Defaults to 'local'.
    _ : Dict[str, Any]
        User authentication and authorization (unused).

    Returns
    -------
    dict
        A success message indicating the service was updated.

    Raises
    ------
    HTTPException
        - 401: Authentication required
        - 403: Organization membership required (if enabled)
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

        updated_id = patch_service(
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
