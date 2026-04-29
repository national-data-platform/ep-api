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
        "If the dataset name is already in use in PRE-CKAN (which "
        "happens when local CKAN and PRE-CKAN are pointed at the same "
        "instance), the publish is retried automatically with a "
        "timestamp suffix on both `name` and `title`, so the publish "
        "keeps succeeding. The response will include a `warning` field "
        "describing the rename.\n\n"
        "### Requirements\n"
        "- PRE-CKAN must be enabled in the configuration\n"
        "- The dataset must exist in the local catalog\n\n"
        "### Authorization\n"
        "This endpoint requires authentication.\n\n"
        "### Example Response\n"
        "```json\n"
        "{\n"
        '    "id": "12345678-abcd-efgh-ijkl-1234567890ab",\n'
        '    "name": "my-dataset",\n'
        '    "title": "My Dataset",\n'
        '    "warning": null,\n'
        '    "message": "Dataset published to PRE-CKAN successfully"\n'
        "}\n"
        "```\n"
    ),
    responses={
        201: {
            "description": (
                "Dataset published successfully. If the requested name was "
                "already in use in PRE-CKAN, the dataset is still published "
                "with a timestamped name and the response includes a "
                "'warning' field describing the automatic rename."
            ),
            "content": {
                "application/json": {
                    "examples": {
                        "published": {
                            "summary": "Published with the original name",
                            "value": {
                                "id": "12345678-abcd-efgh-ijkl-1234567890ab",
                                "name": "my-dataset",
                                "title": "My Dataset",
                                "warning": None,
                                "message": (
                                    "Dataset published to PRE-CKAN successfully"
                                ),
                            },
                        },
                        "auto_renamed": {
                            "summary": (
                                "Published with an auto-generated timestamp "
                                "suffix because the name was already in use"
                            ),
                            "value": {
                                "id": "12345678-abcd-efgh-ijkl-1234567890ab",
                                "name": "my-dataset-20260429170000",
                                "title": "My Dataset (2026-04-29 17:00:00)",
                                "warning": (
                                    "A dataset named 'my-dataset' already "
                                    "exists in PRE-CKAN. This dataset was "
                                    "published as "
                                    "'my-dataset-20260429170000' with title "
                                    "'My Dataset (2026-04-29 17:00:00)'."
                                ),
                                "message": (
                                    "Dataset published to PRE-CKAN successfully"
                                ),
                            },
                        },
                    }
                }
            },
        },
        400: {
            "description": "Bad Request",
            "content": {
                "application/json": {
                    "example": {"detail": "PRE-CKAN is disabled and cannot be used."}
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
        result = publish_dataset_to_preckan(
            dataset_id=dataset_id,
            user_info=user_info,
        )

        logger.info(
            f"Dataset '{dataset_id}' published to PRE-CKAN "
            f"with new ID: {result['id']}"
        )

        return {
            "id": result["id"],
            "name": result["name"],
            "title": result["title"],
            "warning": result["warning"],
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
