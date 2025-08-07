# api/routes/update_routes/patch_s3.py

from typing import Any, Dict, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status

from api.config.ckan_settings import ckan_settings
from api.models.update_s3_model import S3ResourceUpdateRequest
from api.services.auth_services import get_user_for_write_operation
from api.services.s3_services import patch_s3

router = APIRouter()


@router.patch(
    "/s3/{resource_id}",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="Partially update an existing S3 resource",
    description=(
        "Partially update an existing S3 resource and its associated metadata.\n\n"
        "Only updates the fields that are provided, leaving others "
        "unchanged. This is useful when you only want to modify specific "
        "attributes without affecting the rest of the S3 resource.\n\n"
        "### Path Parameters\n"
        "- **resource_id**: The unique identifier of the S3 resource to update\n\n"
        "### Optional Fields (only provide fields to update)\n"
        "- **resource_name**: Unique name for the S3 resource (lowercase, no spaces)\n"
        "- **resource_title**: Human-readable title of the S3 resource\n"
        "- **owner_org**: Organization ID that owns this S3 resource\n"
        "- **resource_s3**: The S3 URL or URI pointing to the resource location\n"
        "- **notes**: Description or additional notes about the S3 resource\n"
        "- **extras**: Additional metadata (will be merged with existing)\n\n"
        "### Query Parameter\n"
        "Use `?server=local` or `?server=pre_ckan` to pick the CKAN instance. "
        "Defaults to 'local' if not provided.\n\n"
        "### Authorization\n"
        "This endpoint requires authentication. If organization-based "
        "access control is enabled, only users belonging to the configured "
        "organization can update S3 resources.\n\n"
        "### Example Payload (partial update)\n"
        "```json\n"
        "{\n"
        '    "resource_s3": "s3://new-bucket/updated-path/resource.csv",\n'
        '    "resource_title": "Updated S3 Resource Title",\n'
        '    "extras": {\n'
        '        "version": "2.1",\n'
        '        "last_updated": "2024-01-15",\n'
        '        "file_format": "CSV",\n'
        '        "size_bytes": "1048576"\n'
        "    }\n"
        "}\n"
        "```\n"
        "Note: Only `resource_s3`, `resource_title` and `extras` will be updated. "
        "All other fields remain unchanged, and the new extras will be merged "
        "with existing ones.\n"
    ),
    responses={
        200: {
            "description": "S3 resource partially updated successfully",
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
                    "example": {"detail": "Error updating S3 resource: <error message>"}
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
async def patch_s3_resource(
    resource_id: str,
    data: S3ResourceUpdateRequest,
    server: Literal["local", "pre_ckan"] = Query(
        "local", description="Choose 'local' or 'pre_ckan'. Defaults to 'local'."
    ),
    _: Dict[str, Any] = Depends(get_user_for_write_operation),
):
    """
    Partially update an existing S3 resource in CKAN.

    Only updates the fields that are provided in the request, leaving all
    other fields unchanged. This is ideal for making small updates without
    needing to provide the complete S3 resource information.

    Parameters
    ----------
    resource_id : str
        The unique identifier of the S3 resource to patch.
    data : S3ResourceUpdateRequest
        The partial S3 resource update information.
    server : Literal['local', 'pre_ckan']
        CKAN instance to use. Defaults to 'local'.
    _ : Dict[str, Any]
        User authentication and authorization (unused).

    Returns
    -------
    dict
        A success message indicating the S3 resource was updated.

    Raises
    ------
    HTTPException
        - 401: Authentication required
        - 403: Organization membership required (if enabled)
        - 400: for update errors or invalid server config
        - 404: if S3 resource not found
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

        updated_id = await patch_s3(
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
            raise HTTPException(status_code=404, detail="S3 resource not found")
        raise HTTPException(
            status_code=400, detail=f"Error updating S3 resource: {error_msg}"
        )
