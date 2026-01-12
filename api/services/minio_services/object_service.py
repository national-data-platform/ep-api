from typing import List, Optional, Dict, Any, BinaryIO
from unittest.mock import Mock
from minio.error import S3Error
from api.services.minio_services.minio_client import minio_client
from api.models.minio_models import (
    ObjectInfo,
    ObjectListResponse,
    ObjectUploadResponse,
    ObjectMetadataResponse,
    PresignedUrlResponse,
)
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)


def create_s3_error(message: str, code: str) -> S3Error:
    """Create a properly formatted S3Error with all required parameters."""
    mock_response = Mock()
    mock_response.status = 400
    mock_response.data = b""
    mock_response.headers = {}
    return S3Error(code, message, "resource", "request_id", "host_id", mock_response)


async def upload_object(
    bucket_name: str,
    object_key: str,
    file_data: BinaryIO,
    content_type: Optional[str] = None,
    metadata: Optional[Dict[str, str]] = None,
) -> ObjectUploadResponse:
    """
    Upload an object to a bucket.

    Args:
        bucket_name: Name of the bucket
        object_key: Key/name of the object
        file_data: File data to upload
        content_type: Optional content type
        metadata: Optional custom metadata

    Returns:
        ObjectUploadResponse with upload details

    Raises:
        S3Error: If upload fails
    """
    try:
        client = minio_client.client

        # Check if bucket exists
        if not client.bucket_exists(bucket_name):
            raise create_s3_error(
                f"Bucket '{bucket_name}' does not exist", "NoSuchBucket"
            )

        # Get file size for put_object
        file_data.seek(0, 2)  # Seek to end
        file_size = file_data.tell()
        file_data.seek(0)  # Reset to beginning

        # Upload object
        result = client.put_object(
            bucket_name=bucket_name,
            object_name=object_key,
            data=file_data,
            length=file_size,
            content_type=content_type,
            metadata=metadata,
        )

        # Get object info to return size
        object_stat = client.stat_object(bucket_name, object_key)

        logger.info(f"Object '{object_key}' uploaded to bucket '{bucket_name}'")
        return ObjectUploadResponse(
            bucket=bucket_name, key=object_key, size=object_stat.size, etag=result.etag
        )

    except S3Error as e:
        logger.error(
            f"Failed to upload object '{object_key}' to bucket '{bucket_name}': {str(e)}"
        )
        raise
    except Exception as e:
        logger.error(f"Unexpected error uploading object '{object_key}': {str(e)}")
        raise create_s3_error(str(e), "InternalError")


async def list_objects(
    bucket_name: str, prefix: Optional[str] = None
) -> ObjectListResponse:
    """
    List objects in a bucket.

    Args:
        bucket_name: Name of the bucket
        prefix: Optional prefix to filter objects

    Returns:
        ObjectListResponse with list of objects

    Raises:
        S3Error: If listing fails
    """
    try:
        client = minio_client.client

        # Check if bucket exists
        if not client.bucket_exists(bucket_name):
            raise create_s3_error(
                f"Bucket '{bucket_name}' does not exist", "NoSuchBucket"
            )

        # List objects
        objects = client.list_objects(bucket_name, prefix=prefix, recursive=True)

        object_list = []
        for obj in objects:
            object_list.append(
                ObjectInfo(
                    key=obj.object_name,
                    size=obj.size,
                    etag=obj.etag,
                    last_modified=obj.last_modified,
                    content_type=None,  # Not available in list_objects
                )
            )

        logger.info(f"Listed {len(object_list)} objects from bucket '{bucket_name}'")
        return ObjectListResponse(objects=object_list, prefix=prefix)

    except S3Error as e:
        logger.error(f"Failed to list objects in bucket '{bucket_name}': {str(e)}")
        raise
    except Exception as e:
        logger.error(
            f"Unexpected error listing objects in bucket '{bucket_name}': {str(e)}"
        )
        raise create_s3_error(str(e), "InternalError")


async def get_object_metadata(
    bucket_name: str, object_key: str
) -> ObjectMetadataResponse:
    """
    Get object metadata.

    Args:
        bucket_name: Name of the bucket
        object_key: Key/name of the object

    Returns:
        ObjectMetadataResponse with object metadata

    Raises:
        S3Error: If object doesn't exist or operation fails
    """
    try:
        client = minio_client.client

        # Get object statistics
        object_stat = client.stat_object(bucket_name, object_key)

        return ObjectMetadataResponse(
            key=object_key,
            size=object_stat.size,
            content_type=object_stat.content_type or "application/octet-stream",
            last_modified=object_stat.last_modified,
            etag=object_stat.etag,
            metadata=object_stat.metadata or {},
        )

    except S3Error as e:
        logger.error(
            f"Failed to get metadata for object '{object_key}' in bucket '{bucket_name}': {str(e)}"
        )
        raise
    except Exception as e:
        logger.error(f"Unexpected error getting object metadata: {str(e)}")
        raise create_s3_error(str(e), "InternalError")


async def delete_object(bucket_name: str, object_key: str) -> bool:
    """
    Delete an object from a bucket.

    Args:
        bucket_name: Name of the bucket
        object_key: Key/name of the object

    Returns:
        True if object was deleted successfully

    Raises:
        S3Error: If deletion fails
    """
    try:
        client = minio_client.client

        # Check if object exists
        try:
            client.stat_object(bucket_name, object_key)
        except S3Error as e:
            if e.code == "NoSuchKey":
                raise create_s3_error(
                    f"Object '{object_key}' does not exist in bucket '{bucket_name}'",
                    "NoSuchKey",
                )
            raise

        # Delete object
        client.remove_object(bucket_name, object_key)
        logger.info(f"Object '{object_key}' deleted from bucket '{bucket_name}'")
        return True

    except S3Error as e:
        logger.error(
            f"Failed to delete object '{object_key}' from bucket '{bucket_name}': {str(e)}"
        )
        raise
    except Exception as e:
        logger.error(f"Unexpected error deleting object '{object_key}': {str(e)}")
        raise create_s3_error(str(e), "InternalError")


async def generate_presigned_upload_url(
    bucket_name: str, object_key: str, expires_in: int = 3600
) -> PresignedUrlResponse:
    """
    Generate a presigned URL for uploading an object.

    Args:
        bucket_name: Name of the bucket
        object_key: Key/name of the object
        expires_in: URL expiration time in seconds

    Returns:
        PresignedUrlResponse with presigned URL

    Raises:
        S3Error: If URL generation fails
    """
    try:
        client = minio_client.client

        # Check if bucket exists
        if not client.bucket_exists(bucket_name):
            raise create_s3_error(
                f"Bucket '{bucket_name}' does not exist", "NoSuchBucket"
            )

        # Generate presigned URL
        url = client.presigned_put_object(
            bucket_name=bucket_name,
            object_name=object_key,
            expires=timedelta(seconds=expires_in),
        )

        logger.info(
            f"Generated presigned upload URL for '{object_key}' in bucket '{bucket_name}'"
        )
        return PresignedUrlResponse(url=url, expires_in=expires_in)

    except S3Error as e:
        logger.error(f"Failed to generate presigned upload URL: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error generating presigned upload URL: {str(e)}")
        raise create_s3_error(str(e), "InternalError")


async def generate_presigned_download_url(
    bucket_name: str, object_key: str, expires_in: int = 3600
) -> PresignedUrlResponse:
    """
    Generate a presigned URL for downloading an object.

    Args:
        bucket_name: Name of the bucket
        object_key: Key/name of the object
        expires_in: URL expiration time in seconds

    Returns:
        PresignedUrlResponse with presigned URL

    Raises:
        S3Error: If URL generation fails
    """
    try:
        client = minio_client.client

        # Check if object exists
        try:
            client.stat_object(bucket_name, object_key)
        except S3Error as e:
            if e.code == "NoSuchKey":
                raise create_s3_error(
                    f"Object '{object_key}' does not exist in bucket '{bucket_name}'",
                    "NoSuchKey",
                )
            raise

        # Generate presigned URL
        url = client.presigned_get_object(
            bucket_name=bucket_name,
            object_name=object_key,
            expires=timedelta(seconds=expires_in),
        )

        logger.info(
            f"Generated presigned download URL for '{object_key}' in bucket '{bucket_name}'"
        )
        return PresignedUrlResponse(url=url, expires_in=expires_in)

    except S3Error as e:
        logger.error(f"Failed to generate presigned download URL: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error generating presigned download URL: {str(e)}")
        raise create_s3_error(str(e), "InternalError")
