# api/routes/resource_routes/resource_by_id.py
"""
Resource management endpoints by resource ID only.

These endpoints allow managing resources without needing the parent dataset ID.
"""

from typing import Any, Dict, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status

from api.config import ckan_settings
from api.models.resource_patch_model import ResourcePatchRequest
from api.repositories import CKANRepository
from api.services import dataset_services
from api.services.auth_services import get_user_for_write_operation

router = APIRouter()


@router.get(
    "/resource/{resource_id}",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="Get a resource by ID",
    description=(
        "Retrieve a resource using only its ID, without needing the dataset ID.\n\n"
        "### Query Parameter\n"
        "Use `?server=local` or `?server=pre_ckan` to select the catalog instance. "
        "Defaults to 'local'."
    ),
    responses={
        200: {
            "description": "Resource retrieved successfully",
            "content": {
                "application/json": {
                    "example": {
                        "id": "abc123",
                        "name": "my-resource",
                        "url": "https://example.com/data.csv",
                        "description": "Sample resource",
                        "format": "CSV",
                        "package_id": "dataset-123",
                    }
                }
            },
        },
        404: {
            "description": "Resource not found",
            "content": {
                "application/json": {"example": {"detail": "Resource not found"}}
            },
        },
    },
)
async def get_resource_by_id(
    resource_id: str,
    server: Literal["local", "pre_ckan"] = Query(
        "local", description="Choose 'local' or 'pre_ckan'. Defaults to 'local'."
    ),
):
    """
    Get a resource by its ID.

    Parameters
    ----------
    resource_id : str
        The ID of the resource to retrieve
    server : str
        Which catalog to use ('local' or 'pre_ckan')
    """
    try:
        repository = None
        if server == "pre_ckan":
            if not ckan_settings.pre_ckan_enabled:
                raise HTTPException(
                    status_code=400, detail="Pre-CKAN is disabled and cannot be used."
                )
            repository = CKANRepository(ckan_settings.pre_ckan)

        result = dataset_services.get_resource(
            resource_id=resource_id, repository=repository
        )
        return result

    except Exception as e:
        error_msg = str(e)
        if "not found" in error_msg.lower():
            raise HTTPException(status_code=404, detail="Resource not found")
        raise HTTPException(status_code=400, detail=error_msg)


@router.patch(
    "/resource/{resource_id}",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="Update a resource by ID",
    description=(
        "Partially update a resource using only its ID.\n\n"
        "Only updates the fields that are provided, leaving others unchanged.\n\n"
        "### Optional Fields\n"
        "- **name**: New name for the resource\n"
        "- **url**: New URL for the resource\n"
        "- **description**: New description\n"
        "- **format**: New format type (CSV, JSON, PDF, etc.)\n\n"
        "### Query Parameter\n"
        "Use `?server=local` or `?server=pre_ckan` to select the catalog instance."
    ),
    responses={
        200: {
            "description": "Resource updated successfully",
            "content": {
                "application/json": {
                    "example": {
                        "id": "abc123",
                        "name": "updated-resource",
                        "url": "https://example.com/data.csv",
                        "description": "Updated description",
                        "format": "CSV",
                    }
                }
            },
        },
        404: {
            "description": "Resource not found",
            "content": {
                "application/json": {"example": {"detail": "Resource not found"}}
            },
        },
    },
)
async def patch_resource_by_id(
    resource_id: str,
    data: ResourcePatchRequest,
    server: Literal["local", "pre_ckan"] = Query(
        "local", description="Choose 'local' or 'pre_ckan'. Defaults to 'local'."
    ),
    _: Dict[str, Any] = Depends(get_user_for_write_operation),
):
    """
    Partially update a resource by its ID.

    Parameters
    ----------
    resource_id : str
        The ID of the resource to update
    data : ResourcePatchRequest
        The partial resource update information
    server : str
        Which catalog to use ('local' or 'pre_ckan')
    """
    try:
        repository = None
        if server == "pre_ckan":
            if not ckan_settings.pre_ckan_enabled:
                raise HTTPException(
                    status_code=400, detail="Pre-CKAN is disabled and cannot be used."
                )
            repository = CKANRepository(ckan_settings.pre_ckan)

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
        raise HTTPException(
            status_code=400, detail=f"Error updating resource: {error_msg}"
        )


@router.delete(
    "/resource/{resource_id}",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="Delete a resource by ID",
    description=(
        "Delete a resource using only its ID, without needing the dataset ID.\n\n"
        "The parent dataset and other resources remain intact.\n\n"
        "### Query Parameter\n"
        "Use `?server=local` or `?server=pre_ckan` to select the catalog instance."
    ),
    responses={
        200: {
            "description": "Resource deleted successfully",
            "content": {
                "application/json": {
                    "example": {"message": "Resource deleted successfully"}
                }
            },
        },
        404: {
            "description": "Resource not found",
            "content": {
                "application/json": {"example": {"detail": "Resource not found"}}
            },
        },
    },
)
async def delete_resource_by_id(
    resource_id: str,
    server: Literal["local", "pre_ckan"] = Query(
        "local", description="Choose 'local' or 'pre_ckan'. Defaults to 'local'."
    ),
    _: Dict[str, Any] = Depends(get_user_for_write_operation),
):
    """
    Delete a resource by its ID.

    Parameters
    ----------
    resource_id : str
        The ID of the resource to delete
    server : str
        Which catalog to use ('local' or 'pre_ckan')
    """
    try:
        repository = None
        if server == "pre_ckan":
            if not ckan_settings.pre_ckan_enabled:
                raise HTTPException(
                    status_code=400, detail="Pre-CKAN is disabled and cannot be used."
                )
            repository = CKANRepository(ckan_settings.pre_ckan)

        dataset_services.delete_resource(resource_id=resource_id, repository=repository)
        return {"message": f"Resource '{resource_id}' deleted successfully"}

    except Exception as e:
        error_msg = str(e)
        if "not found" in error_msg.lower():
            raise HTTPException(status_code=404, detail="Resource not found")
        raise HTTPException(status_code=400, detail=error_msg)
