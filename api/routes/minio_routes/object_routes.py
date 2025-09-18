from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form, Query, status
from fastapi.responses import StreamingResponse
from minio.error import S3Error
from typing import Optional
from api.models.minio_models import (
    ObjectListResponse, ObjectUploadResponse, ObjectMetadataResponse,
    PresignedUrlRequest, PresignedUrlResponse, ErrorResponse
)
from api.services.minio_services import object_service
from api.services.minio_services.minio_client import minio_client
from api.services.auth_services.get_current_user import get_current_user
from api.config.minio_settings import s3_settings
import io

router = APIRouter(prefix="/s3/objects", tags=["S3"])


@router.post("/{bucket_name}", response_model=ObjectUploadResponse)
async def upload_object(
    bucket_name: str,
    file: UploadFile = File(...),
    object_key: Optional[str] = Form(None),
    current_user=Depends(get_current_user)
):
    """Upload an object to a bucket."""
    if not s3_settings.is_configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="S3 service is not configured"
        )
    
    # Use filename as object key if not provided
    key = object_key or file.filename
    if not key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Object key or filename must be provided"
        )
    
    try:
        # Read file content
        content = await file.read()
        file_data = io.BytesIO(content)
        
        return await object_service.upload_object(
            bucket_name=bucket_name,
            object_key=key,
            file_data=file_data,
            content_type=file.content_type
        )
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
            detail=f"Failed to upload object: {str(e)}"
        )


@router.get("/{bucket_name}", response_model=ObjectListResponse)
async def list_objects(
    bucket_name: str,
    prefix: Optional[str] = Query(None, description="Object prefix filter"),
    current_user=Depends(get_current_user)
):
    """List objects in a bucket."""
    if not s3_settings.is_configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="S3 service is not configured"
        )
    
    try:
        return await object_service.list_objects(bucket_name, prefix)
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
            detail=f"Failed to list objects: {str(e)}"
        )


@router.get("/{bucket_name}/{object_key:path}/metadata", response_model=ObjectMetadataResponse)
async def get_object_metadata(
    bucket_name: str,
    object_key: str,
    current_user=Depends(get_current_user)
):
    """Get object metadata."""
    if not s3_settings.is_configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="S3 service is not configured"
        )
    
    try:
        return await object_service.get_object_metadata(bucket_name, object_key)
    except S3Error as e:
        if e.code == "NoSuchKey":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Object '{object_key}' not found in bucket '{bucket_name}'"
            )
        elif e.code == "NoSuchBucket":
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
            detail=f"Failed to get object metadata: {str(e)}"
        )


@router.post("/{bucket_name}/{object_key:path}/presigned-upload", response_model=PresignedUrlResponse)
async def generate_presigned_upload_url(
    bucket_name: str,
    object_key: str,
    request: PresignedUrlRequest,
    current_user=Depends(get_current_user)
):
    """Generate a presigned URL for uploading an object."""
    if not s3_settings.is_configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="S3 service is not configured"
        )
    
    try:
        return await object_service.generate_presigned_upload_url(
            bucket_name, object_key, request.expires_in
        )
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
            detail=f"Failed to generate presigned upload URL: {str(e)}"
        )


@router.post("/{bucket_name}/{object_key:path}/presigned-download", response_model=PresignedUrlResponse)
async def generate_presigned_download_url(
    bucket_name: str,
    object_key: str,
    request: PresignedUrlRequest,
    current_user=Depends(get_current_user)
):
    """Generate a presigned URL for downloading an object."""
    if not s3_settings.is_configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="S3 service is not configured"
        )
    
    try:
        return await object_service.generate_presigned_download_url(
            bucket_name, object_key, request.expires_in
        )
    except S3Error as e:
        if e.code == "NoSuchKey":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Object '{object_key}' not found in bucket '{bucket_name}'"
            )
        elif e.code == "NoSuchBucket":
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
            detail=f"Failed to generate presigned download URL: {str(e)}"
        )


@router.get("/{bucket_name}/{object_key:path}")
async def download_object(
    bucket_name: str,
    object_key: str,
    current_user=Depends(get_current_user)
):
    """Download an object from a bucket."""
    if not s3_settings.is_configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="S3 service is not configured"
        )
    
    try:
        client = minio_client.client
        
        # Get object metadata first
        metadata = await object_service.get_object_metadata(bucket_name, object_key)
        
        # Get object data
        response = client.get_object(bucket_name, object_key)
        
        # Read all data and close connection immediately
        try:
            content = response.read()
        finally:
            response.close()
            response.release_conn()
        
        return StreamingResponse(
            io.BytesIO(content),
            media_type=metadata.content_type,
            headers={"Content-Disposition": f"attachment; filename={object_key.split('/')[-1]}"}
        )
        
    except S3Error as e:
        if e.code == "NoSuchKey":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Object '{object_key}' not found in bucket '{bucket_name}'"
            )
        elif e.code == "NoSuchBucket":
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
            detail=f"Failed to download object: {str(e)}"
        )


@router.delete("/{bucket_name}/{object_key:path}", response_model=dict)
async def delete_object(
    bucket_name: str,
    object_key: str,
    current_user=Depends(get_current_user)
):
    """Delete an object from a bucket."""
    if not s3_settings.is_configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="S3 service is not configured"
        )
    
    try:
        success = await object_service.delete_object(bucket_name, object_key)
        return {"message": f"Object '{object_key}' deleted successfully", "success": success}
    except S3Error as e:
        if e.code == "NoSuchKey":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Object '{object_key}' not found in bucket '{bucket_name}'"
            )
        elif e.code == "NoSuchBucket":
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
            detail=f"Failed to delete object: {str(e)}"
        )