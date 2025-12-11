# api/routes/delete_routes/delete_resource_from_dataset.py

from typing import Literal

from fastapi import APIRouter, HTTPException, Query

from api.config import catalog_settings, ckan_settings
from api.repositories import CKANRepository
from api.services import dataset_services

router = APIRouter()


@router.delete(
    "/dataset/{dataset_id}/resource/{resource_id}",
    response_model=dict,
    summary="Delete a resource from a dataset",
    description=(
        "Delete a single resource from a dataset without deleting the "
        "dataset itself. The dataset and other resources remain intact."
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
        400: {
            "description": "Bad Request",
            "content": {
                "application/json": {
                    "example": {"detail": "Error message explaining the bad request"}
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
async def delete_resource_from_dataset(
    dataset_id: str,
    resource_id: str,
    server: Literal["local", "pre_ckan"] = Query(
        "local", description="Choose 'local' or 'pre_ckan'. Defaults to 'local'."
    ),
):
    """
    Delete a single resource from a dataset.

    This endpoint removes only the specified resource from the dataset.
    The dataset itself and any other resources it contains remain unchanged.

    Parameters
    ----------
    dataset_id : str
        The ID or name of the dataset (for reference/validation)
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

        dataset_services.delete_resource(
            resource_id=resource_id, repository=repository
        )
        return {"message": f"Resource '{resource_id}' deleted successfully"}

    except Exception as e:
        error_msg = str(e)
        if "not found" in error_msg.lower():
            raise HTTPException(status_code=404, detail="Resource not found")
        if "No scheme supplied" in error_msg:
            raise HTTPException(
                status_code=400,
                detail="Pre-CKAN server is not configured or unreachable.",
            )
        raise HTTPException(status_code=400, detail=error_msg)
