# api/routes/update_routes/patch_resource.py

from typing import Any, Dict, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status

from api.config import ckan_settings
from api.models.resource_patch_model import ResourcePatchRequest
from api.repositories import CKANRepository
from api.services import dataset_services
from api.services.auth_services import get_user_for_write_operation

router = APIRouter()


@router.patch(
    "/dataset/{dataset_id}/resource/{resource_id}",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="Partially update a resource",
    description=(
        "Partially update a resource within a dataset.\n\n"
        "Only updates the fields that are provided, leaving others "
        "unchanged. The dataset itself remains unmodified.\n\n"
        "### Path Parameters\n"
        "- **dataset_id**: The ID or name of the dataset (for reference)\n"
        "- **resource_id**: The ID of the resource to update\n\n"
        "### Optional Fields (only provide fields to update)\n"
        "- **name**: New name for the resource\n"
        "- **url**: New URL for the resource\n"
        "- **description**: New description for the resource\n"
        "- **format**: New format type (CSV, JSON, PDF, etc.)\n\n"
        "### Query Parameter\n"
        "Use `?server=local` or `?server=pre_ckan` to pick the catalog instance. "
        "Defaults to 'local' if not provided.\n\n"
        "### Authorization\n"
        "This endpoint requires authentication. If organization-based "
        "access control is enabled, only users belonging to the configured "
        "organization can update resources.\n\n"
        "### Example Payload\n"
        "```json\n"
        "{\n"
        '    "name": "updated-resource-name",\n'
        '    "description": "Updated description"\n'
        "}\n"
        "```\n"
    ),
    responses={
        200: {
            "description": "Resource updated successfully",
            "content": {
                "application/json": {
                    "example": {
                        "id": "abc123",
                        "name": "updated-resource-name",
                        "url": "https://example.com/data.csv",
                        "description": "Updated description",
                        "format": "CSV",
                    }
                }
            },
        },
        400: {
            "description": "Bad Request",
            "content": {
                "application/json": {
                    "example": {"detail": "Error updating resource: <error message>"}
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
async def patch_resource_endpoint(
    dataset_id: str,
    resource_id: str,
    data: ResourcePatchRequest,
    server: Literal["local", "pre_ckan"] = Query(
        "local", description="Choose 'local' or 'pre_ckan'. Defaults to 'local'."
    ),
    _: Dict[str, Any] = Depends(get_user_for_write_operation),
):
    """
    Partially update a resource within a dataset.

    Parameters
    ----------
    dataset_id : str
        The ID or name of the dataset (for reference/validation)
    resource_id : str
        The ID of the resource to patch
    data : ResourcePatchRequest
        The partial resource update information
    server : str
        Which catalog to use ('local' or 'pre_ckan')

    Returns
    -------
    dict
        Updated resource data
    """
    try:
        repository = None
        if server == "pre_ckan":
            if not ckan_settings.ckan_settings.pre_ckan_enabled:
                raise HTTPException(
                    status_code=400, detail="Pre-CKAN is disabled and cannot be used."
                )
            repository = CKANRepository(ckan_settings.ckan_settings.pre_ckan)

        result = dataset_services.patch_resource(
            resource_id=resource_id,
            name=data.name,
            url=data.url,
            description=data.description,
            format=data.format,
            repository=repository,
        )
        return result

    except HTTPException as he:
        raise he
    except Exception as e:
        error_msg = str(e)
        if "not found" in error_msg.lower():
            raise HTTPException(status_code=404, detail="Resource not found")
        if "No scheme supplied" in error_msg:
            raise HTTPException(
                status_code=400,
                detail="Pre-CKAN server is not configured or unreachable.",
            )
        raise HTTPException(status_code=400, detail=f"Error updating resource: {error_msg}")
