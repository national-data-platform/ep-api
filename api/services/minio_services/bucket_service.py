from typing import List
from unittest.mock import Mock
from minio.error import S3Error
from api.services.minio_services.minio_client import minio_client
from api.models.minio_models import BucketInfo, BucketListResponse
import logging

logger = logging.getLogger(__name__)


def create_s3_error(message: str, code: str) -> S3Error:
    """Create a properly formatted S3Error with all required parameters."""
    mock_response = Mock()
    mock_response.status = 400
    mock_response.data = b""
    mock_response.headers = {}
    return S3Error(code, message, "resource", "request_id", "host_id", mock_response)


async def create_bucket(bucket_name: str, region: str = None) -> bool:
    """
    Create a new bucket.
    
    Args:
        bucket_name: Name of the bucket to create
        region: Optional region for the bucket
    
    Returns:
        True if bucket was created successfully
    
    Raises:
        S3Error: If bucket creation fails
        ValueError: If bucket name is invalid
    """
    try:
        client = minio_client.client
        
        # Check if bucket already exists
        if client.bucket_exists(bucket_name):
            raise create_s3_error(f"Bucket '{bucket_name}' already exists", "BucketAlreadyExists")
        
        # Create bucket
        client.make_bucket(bucket_name, location=region)
        logger.info(f"Bucket '{bucket_name}' created successfully")
        return True
        
    except S3Error as e:
        logger.error(f"Failed to create bucket '{bucket_name}': {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error creating bucket '{bucket_name}': {str(e)}")
        raise create_s3_error(str(e), "InternalError")


async def list_buckets() -> BucketListResponse:
    """
    List all buckets.
    
    Returns:
        BucketListResponse with list of buckets
    
    Raises:
        S3Error: If listing buckets fails
    """
    try:
        client = minio_client.client
        buckets = client.list_buckets()
        
        bucket_list = [
            BucketInfo(
                name=bucket.name,
                creation_date=bucket.creation_date
            )
            for bucket in buckets
        ]
        
        logger.info(f"Listed {len(bucket_list)} buckets")
        return BucketListResponse(buckets=bucket_list)
        
    except S3Error as e:
        logger.error(f"Failed to list buckets: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error listing buckets: {str(e)}")
        raise create_s3_error(str(e), "InternalError")


async def get_bucket_info(bucket_name: str) -> BucketInfo:
    """
    Get information about a specific bucket.
    
    Args:
        bucket_name: Name of the bucket
    
    Returns:
        BucketInfo with bucket details
    
    Raises:
        S3Error: If bucket doesn't exist or operation fails
    """
    try:
        client = minio_client.client
        
        # Check if bucket exists
        if not client.bucket_exists(bucket_name):
            raise create_s3_error(f"Bucket '{bucket_name}' does not exist", "NoSuchBucket")
        
        # Get bucket creation date from bucket list
        buckets = client.list_buckets()
        for bucket in buckets:
            if bucket.name == bucket_name:
                return BucketInfo(
                    name=bucket.name,
                    creation_date=bucket.creation_date
                )
        
        # If not found in list (shouldn't happen), return basic info
        return BucketInfo(name=bucket_name, creation_date=None)
        
    except S3Error as e:
        logger.error(f"Failed to get bucket info for '{bucket_name}': {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error getting bucket info for '{bucket_name}': {str(e)}")
        raise create_s3_error(str(e), "InternalError")


async def delete_bucket(bucket_name: str) -> bool:
    """
    Delete a bucket (must be empty).
    
    Args:
        bucket_name: Name of the bucket to delete
    
    Returns:
        True if bucket was deleted successfully
    
    Raises:
        S3Error: If bucket doesn't exist, is not empty, or deletion fails
    """
    try:
        client = minio_client.client
        
        # Check if bucket exists
        if not client.bucket_exists(bucket_name):
            raise create_s3_error(f"Bucket '{bucket_name}' does not exist", "NoSuchBucket")
        
        # Check if bucket is empty
        objects = list(client.list_objects(bucket_name, recursive=True))
        if objects:
            raise create_s3_error(f"Bucket '{bucket_name}' is not empty", "BucketNotEmpty")
        
        # Delete bucket
        client.remove_bucket(bucket_name)
        logger.info(f"Bucket '{bucket_name}' deleted successfully")
        return True
        
    except S3Error as e:
        logger.error(f"Failed to delete bucket '{bucket_name}': {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error deleting bucket '{bucket_name}': {str(e)}")
        raise create_s3_error(str(e), "InternalError")