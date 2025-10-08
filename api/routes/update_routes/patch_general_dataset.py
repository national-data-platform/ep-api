# api/routes/update_routes/patch_general_dataset.py

from typing import Any, Dict, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status

from api.config import catalog_settings, ckan_settings
from api.models.general_dataset_request_model import GeneralDatasetUpdateRequest
from api.repositories import CKANRepository
from api.services.auth_services import get_user_for_write_operation
from api.services.dataset_services.general_dataset import patch_general_dataset

router = APIRouter()


@router.patch(
    "/dataset/{dataset_id}",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="Partially update an existing general dataset",
    description=(
        "Partially update an existing general dataset in CKAN.\n\n"
        "Only updates the fields that are provided, leaving others "
        "unchanged. This is useful when you only want to modify specific "
        "attributes without affecting the rest of the dataset.\n\n"
        "### Path Parameters\n"
        "- **dataset_id**: The unique identifier of the dataset to update\n\n"
        "### Optional Fields (only provide fields to update)\n"
        "- **name**: Unique name for the dataset (lowercase, no spaces)\n"
        "- **title**: Human-readable title of the dataset\n"
        "- **owner_org**: Organization ID that owns this dataset\n"
        "- **notes**: Description or notes about the dataset\n"
        "- **tags**: List of tags for categorizing the dataset\n"
        "- **extras**: Additional metadata (will be merged with existing)\n"
        "- **resources**: List of resources associated with this dataset\n"
        "- **private**: Whether the dataset is private\n"
        "- **license_id**: License identifier for the dataset\n"
        "- **version**: Version of the dataset\n\n"
        "### Query Parameter\n"
        "Use `?server=local` or `?server=pre_ckan` to pick the CKAN instance. "
        "Defaults to 'local' if not provided.\n\n"
        "### Authorization\n"
        "This endpoint requires authentication. If organization-based "
        "access control is enabled, only users belonging to the configured "
        "organization can update datasets.\n\n"
        "### Example Payload (partial update)\n"
        "```json\n"
        "{\n"
        '    "title": "Updated Dataset Title",\n'
        '    "extras": {\n'
        '        "version": "1.1",\n'
        '        "last_modified": "2024-01-15"\n'
        "    }\n"
        "}\n"
        "```\n"
        "Note: Only `title` and `extras` will be updated. All other fields "
        "remain unchanged, and the new extras will be merged with existing "
        "ones.\n"
    ),
    responses={
        200: {
            "description": "Dataset partially updated successfully",
            "content": {
                "application/json": {
                    "example": {"message": "Dataset updated successfully"}
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
                    "example": {"detail": "Error updating dataset: <error message>"}
                }
            },
        },
        404: {
            "description": "Not Found",
            "content": {
                "application/json": {"example": {"detail": "Dataset not found"}}
            },
        },
    },
)
async def patch_general_dataset_endpoint(
    dataset_id: str,
    data: GeneralDatasetUpdateRequest,
    server: Literal["local", "pre_ckan"] = Query(
        "local", description="Choose 'local' or 'pre_ckan'. Defaults to 'local'."
    ),
    _: Dict[str, Any] = Depends(get_user_for_write_operation),
):
    """
    Partially update a general dataset by dataset_id.

    Only updates the fields that are provided in the request, leaving all
    other fields unchanged. This is ideal for making small updates without
    needing to provide the complete dataset information.

    Parameters
    ----------
    dataset_id : str
        The unique identifier of the dataset to patch.
    data : GeneralDatasetUpdateRequest
        The partial dataset update information.
    server : Literal['local', 'pre_ckan']
        CKAN instance to use. Defaults to 'local'.
    _ : Dict[str, Any]
        User authentication and authorization (unused).

    Returns
    -------
    dict
        A success message indicating the dataset was updated.

    Raises
    ------
    HTTPException
        - 401: Authentication required
        - 403: Organization membership required (if enabled)
        - 400: for update errors or invalid server config
        - 404: if dataset not found
    """
    try:
        # Determine which repository to use based on server parameter
        if server == "pre_ckan":
            if not ckan_settings.pre_ckan_enabled:
                raise HTTPException(
                    status_code=400, detail="Pre-CKAN is disabled and cannot be used."
                )
            repository = CKANRepository(ckan_settings.pre_ckan)
        else:
            # Use local catalog (CKAN or MongoDB based on configuration)
            repository = catalog_settings.local_catalog

        # Convert ResourceRequest objects to dictionaries
        resources = None
        if data.resources:
            resources = [resource.dict() for resource in data.resources]

        updated_id = patch_general_dataset(
            dataset_id=dataset_id,
            name=data.name,
            title=data.title,
            owner_org=data.owner_org,
            notes=data.notes,
            tags=data.tags,
            groups=data.groups,
            extras=data.extras,
            resources=resources,
            private=data.private,
            license_id=data.license_id,
            version=data.version,
            repository=repository,
        )

        if not updated_id:
            raise HTTPException(status_code=404, detail="Dataset not found")

        return {"message": "Dataset updated successfully"}

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
            raise HTTPException(status_code=404, detail="Dataset not found")
        raise HTTPException(
            status_code=400, detail=f"Error updating dataset: {error_msg}"
        )
