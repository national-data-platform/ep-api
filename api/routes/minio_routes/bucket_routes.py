from fastapi import APIRouter, HTTPException, Depends, status
from minio.error import S3Error
from api.models.minio_models import (
    BucketCreateRequest, BucketListResponse, BucketInfo, ErrorResponse
)
from api.services.minio_services import bucket_service
from api.services.auth_services.get_current_user import get_current_user
from api.config.minio_settings import s3_settings

router = APIRouter(prefix="/s3/buckets", tags=["S3"])


@router.post("/", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_bucket(
    request: BucketCreateRequest,
    current_user=Depends(get_current_user)
):
    """Create a new bucket."""
    if not s3_settings.is_configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="S3 service is not configured"
        )
    
    try:
        success = await bucket_service.create_bucket(request.name, request.region)
        return {"message": f"Bucket '{request.name}' created successfully", "success": success}
    except S3Error as e:
        if e.code == "BucketAlreadyExists":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Bucket '{request.name}' already exists"
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create bucket: {str(e)}"
        )


@router.get("/", response_model=BucketListResponse)
async def list_buckets(current_user=Depends(get_current_user)):
    """List all buckets."""
    if not s3_settings.is_configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="S3 service is not configured"
        )
    
    try:
        return await bucket_service.list_buckets()
    except S3Error as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list buckets: {str(e)}"
        )


@router.get("/{bucket_name}", response_model=BucketInfo)
async def get_bucket_info(
    bucket_name: str,
    current_user=Depends(get_current_user)
):
    """Get information about a specific bucket."""
    if not s3_settings.is_configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="S3 service is not configured"
        )
    
    try:
        return await bucket_service.get_bucket_info(bucket_name)
    except S3Error as e:
        if e.code == "NoSuchBucket":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Bucket '{bucket_name}' not found"
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get bucket info: {str(e)}"
        )


@router.delete("/{bucket_name}", response_model=dict)
async def delete_bucket(
    bucket_name: str,
    current_user=Depends(get_current_user)
):
    """Delete a bucket (must be empty)."""
    if not s3_settings.is_configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="S3 service is not configured"
        )
    
    try:
        success = await bucket_service.delete_bucket(bucket_name)
        return {"message": f"Bucket '{bucket_name}' deleted successfully", "success": success}
    except S3Error as e:
        if e.code == "NoSuchBucket":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Bucket '{bucket_name}' not found"
            )
        elif e.code == "BucketNotEmpty":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Bucket '{bucket_name}' is not empty"
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete bucket: {str(e)}"
        )