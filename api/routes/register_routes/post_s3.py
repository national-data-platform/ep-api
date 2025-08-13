from typing import Any, Dict, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status

from api.config import ckan_settings
from api.models.s3request_model import S3Request
from api.services.auth_services import get_user_for_write_operation
from api.services.s3_services.add_s3 import add_s3

router = APIRouter()


@router.post(
    "/s3",
    response_model=dict,
    status_code=status.HTTP_201_CREATED,
    summary="Add a new S3 resource",
    description=(
        "Create a new S3 resource.\n\n"
        "Use `?server=local` or `?server=pre_ckan` to choose the CKAN "
        "instance. Defaults to 'local' if not provided.\n\n"
        "### Authorization\n"
        "This endpoint requires authentication. If organization-based "
        "access control is enabled, only users belonging to the configured "
        "organization can create S3 resources."
    ),
    responses={
        201: {
            "description": "Resource created successfully",
            "content": {
                "application/json": {
                    "example": {"id": "12345678-abcd-efgh-ijkl-1234567890ab"}
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
                    "example": {"detail": "Error creating resource: <error message>"}
                }
            },
        },
    },
)
async def create_s3_resource(
    data: S3Request,
    server: Literal["local", "pre_ckan"] = Query(
        "local", description="Specify 'local' or 'pre_ckan'. Defaults to 'local'."
    ),
    user_info: Dict[str, Any] = Depends(get_user_for_write_operation),
):
    """
    Add an S3 resource to CKAN.

    If server='pre_ckan', uses the pre-CKAN instance (if enabled). If
    the URL has no valid scheme, returns a friendly error. Otherwise,
    defaults to local CKAN.

    Parameters
    ----------
    data : S3Request
        Required parameters for creating an S3 resource.
    server : Literal['local', 'pre_ckan']
        Optional query param. Defaults to 'local'.
    user_info : Dict[str, Any]
        User authentication and authorization information.

    Returns
    -------
    dict
        A dictionary containing the ID of the created resource if successful.

    Raises
    ------
    HTTPException
        - 401: Authentication required
        - 403: Organization membership required (if enabled)
        - 400: If there's an error creating the resource or invalid param.
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

        resource_id = add_s3(
            resource_name=data.resource_name,
            resource_title=data.resource_title,
            owner_org=data.owner_org,
            resource_s3=data.resource_s3,
            notes=data.notes,
            extras=data.extras,
            ckan_instance=ckan_instance,
            user_info=user_info,
        )
        return {"id": resource_id}

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
        raise HTTPException(status_code=400, detail=error_msg)
