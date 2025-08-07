# api/routes/update_routes/patch_url.py

from typing import Any, Dict, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status

from api.config.ckan_settings import ckan_settings
from api.models.update_url_model import URLUpdateRequest
from api.services.auth_services import get_user_for_write_operation
from api.services.url_services import patch_url

router = APIRouter()


@router.patch(
    "/url/{resource_id}",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="Partially update an existing URL resource",
    description=(
        "Partially update an existing URL resource in CKAN.\n\n"
        "Only updates the fields that are provided, leaving others "
        "unchanged. This is useful when you only want to modify specific "
        "attributes without affecting the rest of the URL resource.\n\n"
        "### Path Parameters\n"
        "- **resource_id**: The unique identifier of the URL resource to update\n\n"
        "### Optional Fields (only provide fields to update)\n"
        "- **resource_name**: Unique name for the URL resource (lowercase, no spaces)\n"
        "- **resource_title**: Human-readable title of the URL resource\n"
        "- **owner_org**: Organization ID that owns this URL resource\n"
        "- **resource_url**: The URL endpoint or link to the external resource\n"
        "- **file_type**: Data format type of the resource (stream, CSV, TXT, JSON, NetCDF, XML, etc.)\n"
        "- **notes**: Description or additional notes about the URL resource\n"
        "- **extras**: Additional metadata (will be merged with existing)\n"
        "- **mapping**: Data mapping configuration for the URL resource\n"
        "- **processing**: Processing configuration for the URL data\n\n"
        "### Query Parameter\n"
        "Use `?server=local` or `?server=pre_ckan` to pick the CKAN instance. "
        "Defaults to 'local' if not provided.\n\n"
        "### Authorization\n"
        "This endpoint requires authentication. If organization-based "
        "access control is enabled, only users belonging to the configured "
        "organization can update URL resources.\n\n"
        "### Example Payload (partial update)\n"
        "```json\n"
        "{\n"
        '    "resource_url": "https://api.example.com/data/v2/dataset.csv",\n'
        '    "file_type": "CSV",\n'
        '    "resource_title": "Updated External Dataset",\n'
        '    "extras": {\n'
        '        "version": "2.1",\n'
        '        "last_updated": "2024-01-15",\n'
        '        "update_frequency": "daily",\n'
        '        "content_type": "application/csv"\n'
        "    }\n"
        "}\n"
        "```\n"
        "Note: Only `resource_url`, `file_type`, `resource_title` and `extras` "
        "will be updated. All other fields remain unchanged, and the new extras "
        "will be merged with existing ones.\n"
    ),
    responses={
        200: {
            "description": "URL resource partially updated successfully",
            "content": {
                "application/json": {
                    "example": {"message": "Resource updated successfully"}
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
                        "detail": "Error updating URL resource: <error message>"
                    }
                }
            },
        },
        404: {
            "description": "Not Found",
            "content": {
                "application/json": {"example": {"detail": "URL resource not found"}}
            },
        },
    },
)
async def patch_url_resource(
    resource_id: str,
    data: URLUpdateRequest,
    server: Literal["local", "pre_ckan"] = Query(
        "local", description="Choose 'local' or 'pre_ckan'. Defaults to 'local'."
    ),
    _: Dict[str, Any] = Depends(get_user_for_write_operation),
):
    """
    Partially update an existing URL resource in CKAN.

    Only updates the fields that are provided in the request, leaving all
    other fields unchanged. This is ideal for making small updates without
    needing to provide the complete URL resource information.

    Parameters
    ----------
    resource_id : str
        The unique identifier of the URL resource to patch.
    data : URLUpdateRequest
        The partial URL resource update information.
    server : Literal['local', 'pre_ckan']
        CKAN instance to use. Defaults to 'local'.
    _ : Dict[str, Any]
        User authentication and authorization (unused).

    Returns
    -------
    dict
        A success message indicating the URL resource was updated.

    Raises
    ------
    HTTPException
        - 401: Authentication required
        - 403: Organization membership required (if enabled)
        - 400: for update errors or invalid server config
        - 404: if URL resource not found
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

        result = await patch_url(
            resource_id=resource_id,
            resource_name=data.resource_name,
            resource_title=data.resource_title,
            owner_org=data.owner_org,
            resource_url=data.resource_url,
            file_type=data.file_type,
            notes=data.notes,
            extras=data.extras,
            mapping=data.mapping,
            processing=data.processing,
            ckan_instance=ckan_instance,
        )

        return result

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
            raise HTTPException(status_code=404, detail="URL resource not found")
        raise HTTPException(
            status_code=400, detail=f"Error updating URL resource: {error_msg}"
        )
