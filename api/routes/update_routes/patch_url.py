# api/routes/update_routes/patch_url.py

from typing import Any, Dict, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status

from api.config.ckan_settings import ckan_settings
from api.models.update_url_model import URLUpdateRequest
from api.services.auth_services import get_current_user
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
        "- **resource_name**: The unique name of the resource.\n"
        "- **resource_title**: The title of the resource.\n"
        "- **owner_org**: The ID of the organization.\n"
        "- **resource_url**: The URL of the resource.\n"
        "- **file_type**: The file type (`stream`, `CSV`, `TXT`, `JSON`, "
        "`NetCDF`).\n"
        "- **notes**: Additional notes (optional).\n"
        "- **extras**: Additional metadata (will be merged with existing).\n"
        "- **mapping**: Mapping info (optional).\n"
        "- **processing**: Processing info (optional).\n\n"
        "### Query Parameter\n"
        "Use `?server=local` or `?server=pre_ckan` to pick the CKAN instance. "
        "Defaults to 'local' if not provided.\n\n"
        "### Example Payload (partial update)\n"
        "```json\n"
        "{\n"
        '    "resource_url": "http://updated.example.com/data.csv",\n'
        '    "file_type": "CSV",\n'
        '    "extras": {\n'
        '        "version": "2.1",\n'
        '        "last_updated": "2024-01-15"\n'
        "    }\n"
        "}\n"
        "```\n"
        "Note: Only `resource_url`, `file_type` and `extras` will be updated. "
        "All other fields remain unchanged, and the new extras will be merged "
        "with existing ones.\n"
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
        400: {
            "description": "Bad Request",
            "content": {
                "application/json": {
                    "example": {"detail": "Error updating resource: <error>"}
                }
            },
        },
        404: {
            "description": "Not Found",
            "content": {
                "application/json": {"example": {"detail": "Resource not found"}}
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
    _: Dict[str, Any] = Depends(get_current_user),
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
        Keycloak user auth (unused).

    Returns
    -------
    dict
        A success message indicating the URL resource was updated.

    Raises
    ------
    HTTPException
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
    except KeyError as e:
        raise HTTPException(status_code=400, detail=f"Reserved key error: {str(e)}")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid input: {str(e)}")
    except Exception as e:
        error_msg = str(e)
        if "No scheme supplied" in error_msg:
            raise HTTPException(
                status_code=400,
                detail="Pre-CKAN server is not configured or unreachable.",
            )
        if "not found" in error_msg.lower():
            raise HTTPException(status_code=404, detail="Resource not found")
        raise HTTPException(status_code=400, detail=error_msg)