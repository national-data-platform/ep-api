from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


class BucketCreateRequest(BaseModel):
    """Request model for creating a bucket."""
    name: str = Field(..., description="Bucket name")
    region: Optional[str] = Field(None, description="Bucket region")


class BucketInfo(BaseModel):
    """Bucket information model."""
    name: str = Field(..., description="Bucket name")
    creation_date: Optional[datetime] = Field(None, description="Bucket creation date")


class BucketListResponse(BaseModel):
    """Response model for listing buckets."""
    buckets: List[BucketInfo] = Field(..., description="List of buckets")


class ObjectInfo(BaseModel):
    """Object information model."""
    key: str = Field(..., description="Object key/name")
    size: int = Field(..., description="Object size in bytes")
    etag: str = Field(..., description="Object ETag")
    last_modified: datetime = Field(..., description="Last modification date")
    content_type: Optional[str] = Field(None, description="Object content type")


class ObjectListResponse(BaseModel):
    """Response model for listing objects."""
    objects: List[ObjectInfo] = Field(..., description="List of objects")
    prefix: Optional[str] = Field(None, description="Object prefix filter")


class ObjectUploadRequest(BaseModel):
    """Request model for object upload metadata."""
    key: str = Field(..., description="Object key/name")
    content_type: Optional[str] = Field(None, description="Content type")
    metadata: Optional[Dict[str, str]] = Field(None, description="Custom metadata")


class ObjectUploadResponse(BaseModel):
    """Response model for object upload."""
    bucket: str = Field(..., description="Bucket name")
    key: str = Field(..., description="Object key/name")
    size: int = Field(..., description="Uploaded object size")
    etag: str = Field(..., description="Object ETag")


class PresignedUrlRequest(BaseModel):
    """Request model for presigned URL generation."""
    expires_in: int = Field(3600, description="URL expiration time in seconds", ge=1, le=604800)


class PresignedUrlResponse(BaseModel):
    """Response model for presigned URL."""
    url: str = Field(..., description="Presigned URL")
    expires_in: int = Field(..., description="URL expiration time in seconds")


class ObjectMetadataResponse(BaseModel):
    """Response model for object metadata."""
    key: str = Field(..., description="Object key/name")
    size: int = Field(..., description="Object size in bytes")
    content_type: str = Field(..., description="Object content type")
    last_modified: datetime = Field(..., description="Last modification date")
    etag: str = Field(..., description="Object ETag")
    metadata: Dict[str, str] = Field(..., description="Custom metadata")


class ErrorResponse(BaseModel):
    """Error response model."""
    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Detailed error information")