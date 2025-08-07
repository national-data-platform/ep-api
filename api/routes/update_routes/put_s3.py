# api/routes/update_routes/put_s3.py

from typing import Any, Dict, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status

from api.config.ckan_settings import ckan_settings
from api.models.update_s3_model import S3ResourceUpdateRequest
from api.services.auth_services import get_user_for_write_operation
from api.services.s3_services.update_s3 import update_s3

router = APIRouter()


@router.put(
    "/s3/{resource_id}",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="Update an existing S3 resource",
    description=(
        "Update an existing S3 resource and its associated metadata.\n\n"
        "### Optional Fields\n"
        "- **resource_name**: The unique name of the resource.\n"
        "- **resource_title**: The title of the resource.\n"
        "- **owner_org**: The ID of the organization.\n"
        "- **resource_s3**: The S3 URL of the resource.\n"
        "- **notes**: Additional notes.\n"
        "- **extras**: Additional metadata.\n\n"
        "### Query Parameter\n"
        "Use `?server=local` or `?server=pre_ckan` to choose which CKAN "
        "instance to update. Defaults to 'local' if not provided.\n\n"
        "### Authorization\n"
        "This endpoint requires authentication. If organization-based "
        "access control is enabled, only users belonging to the configured "
        "organization can update S3 resources.\n\n"
        "### Example Payload\n"
        "```json\n"
        "{\n"
        '    "resource_name": "updated_resource_name",\n'
        '    "resource_s3": "http://new-s3-url.com/resource"\n'
        "}\n"
        "```\n"
    ),
    responses={
        200: {
            "description": "S3 resource updated successfully",
            "content": {
                "application/json": {
                    "example": {"message": "S3 resource updated successfully"}
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
                    "example": {
                        "detail": ("Error updating S3 resource: <error message>")
                    }
                }
            },
        },
        404: {
            "description": "Not Found",
            "content": {
                "application/json": {"example": {"detail": "S3 resource not found"}}
            },
        },
    },
)
async def update_s3_resource(
    resource_id: str,
    data: S3ResourceUpdateRequest,
    server: Literal["local", "pre_ckan"] = Query(
        "local", description="Choose 'local' or 'pre_ckan'. Defaults to 'local'."
    ),
    _: Dict[str, Any] = Depends(get_user_for_write_operation),
):
    """
    Update an existing S3 resource in CKAN.

    If ?server=pre_ckan is used and pre_ckan is enabled/configured,
    updates the resource in the pre-CKAN instance. Otherwise defaults
    to local CKAN. Returns a 400 error if pre_ckan is disabled or
    missing a valid scheme.

    Parameters
    ----------
    resource_id : str
        The unique identifier of the S3 resource to update.
    data : S3ResourceUpdateRequest
        The updated S3 resource information.
    server : Literal['local', 'pre_ckan']
        CKAN instance to use. Defaults to 'local'.
    _ : Dict[str, Any]
        User authentication and authorization (unused).

    Returns
    -------
    dict
        A success message indicating the resource was updated.

    Raises
    ------
    HTTPException
        - 401: Authentication required
        - 403: Organization membership required (if enabled)
        - 400: for update errors or invalid server config
        - 404: if resource not found
    """
    try:
        # Determine CKAN instance
        if server == "pre_ckan":
            if not ckan_settings.pre_ckan_enabled:
                raise HTTPException(
                    status_code=400, detail="Pre-CKAN is disabled and cannot be used."
                )
            ckan_instance = ckan_settings.pre_ckan
        else:
            ckan_instance = ckan_settings.ckan

        updated_id = await update_s3(
            resource_id=resource_id,
            resource_name=data.resource_name,
            resource_title=data.resource_title,
            owner_org=data.owner_org,
            resource_s3=data.resource_s3,
            notes=data.notes,
            extras=data.extras,
            ckan_instance=ckan_instance,
        )
        if not updated_id:
            raise HTTPException(status_code=404, detail="S3 resource not found")
        return {"message": "S3 resource updated successfully"}

    except Exception as exc:
        error_msg = str(exc)
        if "No scheme supplied" in error_msg:
            raise HTTPException(
                status_code=400,
                detail="Pre-CKAN server is not configured or unreachable.",
            )
        raise HTTPException(status_code=400, detail=error_msg)
