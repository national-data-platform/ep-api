# api/routes/register_routes/publish_dataset.py

"""Endpoint for publishing datasets from local catalog to PRE-CKAN."""

import logging
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, Path, status

from api.services.auth_services import get_user_for_write_operation
from api.services.dataset_services.publish_dataset import publish_dataset_to_preckan

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/dataset/{dataset_id}/publish",
    response_model=dict,
    status_code=status.HTTP_201_CREATED,
    summary="Publish dataset from local catalog to PRE-CKAN",
    description=(
        "Publish (copy) a dataset from the local catalog to PRE-CKAN.\n\n"
        "### Behavior\n"
        "1. Fetches the dataset from the local catalog\n"
        "2. Creates the dataset in PRE-CKAN with the same metadata\n"
        "3. Creates all associated resources in PRE-CKAN\n\n"
        "### Requirements\n"
        "- PRE-CKAN must be enabled in the configuration\n"
        "- The dataset must exist in the local catalog\n"
        "- The dataset name must not already exist in PRE-CKAN\n\n"
        "### Authorization\n"
        "This endpoint requires authentication.\n\n"
        "### Example Response\n"
        "```json\n"
        "{\n"
        '    "id": "12345678-abcd-efgh-ijkl-1234567890ab",\n'
        '    "message": "Dataset published to PRE-CKAN successfully"\n'
        "}\n"
        "```\n"
    ),
    responses={
        201: {
            "description": "Dataset published successfully",
            "content": {
                "application/json": {
                    "example": {
                        "id": "12345678-abcd-efgh-ijkl-1234567890ab",
                        "message": "Dataset published to PRE-CKAN successfully",
                    }
                }
            },
        },
        400: {
            "description": "Bad Request",
            "content": {
                "application/json": {
                    "examples": {
                        "preckan_disabled": {
                            "summary": "PRE-CKAN disabled",
                            "value": {
                                "detail": "PRE-CKAN is disabled and cannot be used."
                            },
                        },
                        "duplicate": {
                            "summary": "Dataset already exists",
                            "value": {
                                "detail": (
                                    "A dataset with name 'my-dataset' "
                                    "already exists in PRE-CKAN."
                                )
                            },
                        },
                    }
                }
            },
        },
        401: {
            "description": "Unauthorized - Authentication required",
            "content": {
                "application/json": {"example": {"detail": "Invalid or expired token"}}
            },
        },
        404: {
            "description": "Dataset not found in local catalog",
            "content": {
                "application/json": {
                    "example": {"detail": "Dataset not found in local catalog: ..."}
                }
            },
        },
        500: {
            "description": "Internal server error",
            "content": {
                "application/json": {
                    "example": {"detail": "Error creating dataset in PRE-CKAN: ..."}
                }
            },
        },
    },
)
async def publish_dataset_endpoint(
    dataset_id: str = Path(..., description="ID or name of the dataset to publish"),
    user_info: Dict[str, Any] = Depends(get_user_for_write_operation),
):
    """
    Publish a dataset from the local catalog to PRE-CKAN.

    This endpoint copies a dataset and its resources from the local
    catalog to PRE-CKAN, enabling promotion of datasets from
    development/local environment to pre-production.

    Parameters
    ----------
    dataset_id : str
        The ID or name of the dataset to publish.
    user_info : Dict[str, Any]
        User authentication and authorization information.

    Returns
    -------
    dict
        A dictionary containing the new dataset ID in PRE-CKAN and
        a success message.

    Raises
    ------
    HTTPException
        - 400: PRE-CKAN disabled or duplicate dataset
        - 401: Authentication required
        - 404: Dataset not found in local catalog
        - 500: Error during publication
    """
    try:
        new_dataset_id = publish_dataset_to_preckan(
            dataset_id=dataset_id,
            user_info=user_info,
        )

        logger.info(
            f"Dataset '{dataset_id}' published to PRE-CKAN "
            f"with new ID: {new_dataset_id}"
        )

        return {
            "id": new_dataset_id,
            "message": "Dataset published to PRE-CKAN successfully",
        }

    except ValueError as exc:
        error_msg = str(exc)
        if "not found" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=error_msg,
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg,
        )
    except Exception as exc:
        logger.error(f"Error publishing dataset to PRE-CKAN: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error publishing dataset: {str(exc)}",
        )
