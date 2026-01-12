import pytest
from datetime import datetime
from pydantic import ValidationError

from api.models.minio_models import (
    BucketCreateRequest,
    BucketInfo,
    BucketListResponse,
    ObjectInfo,
    ObjectListResponse,
    ObjectUploadRequest,
    ObjectUploadResponse,
    PresignedUrlRequest,
    PresignedUrlResponse,
    ObjectMetadataResponse,
    ErrorResponse,
)


class TestBucketModels:
    """Test bucket-related Pydantic models."""

    def test_bucket_create_request_minimal(self):
        """Test BucketCreateRequest with minimal data."""
        request = BucketCreateRequest(name="test-bucket")
        assert request.name == "test-bucket"
        assert request.region is None

    def test_bucket_create_request_with_region(self):
        """Test BucketCreateRequest with region."""
        request = BucketCreateRequest(name="test-bucket", region="us-west-2")
        assert request.name == "test-bucket"
        assert request.region == "us-west-2"

    def test_bucket_create_request_validation_error(self):
        """Test BucketCreateRequest validation errors."""
        with pytest.raises(ValidationError):
            BucketCreateRequest()  # Missing required name field

    def test_bucket_info_minimal(self):
        """Test BucketInfo with minimal data."""
        bucket = BucketInfo(name="test-bucket")
        assert bucket.name == "test-bucket"
        assert bucket.creation_date is None

    def test_bucket_info_with_date(self):
        """Test BucketInfo with creation date."""
        creation_date = datetime(2023, 1, 1, 12, 0, 0)
        bucket = BucketInfo(name="test-bucket", creation_date=creation_date)
        assert bucket.name == "test-bucket"
        assert bucket.creation_date == creation_date

    def test_bucket_list_response_empty(self):
        """Test BucketListResponse with empty list."""
        response = BucketListResponse(buckets=[])
        assert response.buckets == []

    def test_bucket_list_response_with_buckets(self):
        """Test BucketListResponse with multiple buckets."""
        bucket1 = BucketInfo(name="bucket1")
        bucket2 = BucketInfo(name="bucket2")
        response = BucketListResponse(buckets=[bucket1, bucket2])

        assert len(response.buckets) == 2
        assert response.buckets[0].name == "bucket1"
        assert response.buckets[1].name == "bucket2"


class TestObjectModels:
    """Test object-related Pydantic models."""

    def test_object_info_complete(self):
        """Test ObjectInfo with all fields."""
        last_modified = datetime(2023, 1, 1, 12, 0, 0)
        obj = ObjectInfo(
            key="test.txt",
            size=1024,
            etag="abc123",
            last_modified=last_modified,
            content_type="text/plain",
        )

        assert obj.key == "test.txt"
        assert obj.size == 1024
        assert obj.etag == "abc123"
        assert obj.last_modified == last_modified
        assert obj.content_type == "text/plain"

    def test_object_info_minimal(self):
        """Test ObjectInfo with minimal required fields."""
        last_modified = datetime(2023, 1, 1, 12, 0, 0)
        obj = ObjectInfo(
            key="test.txt", size=1024, etag="abc123", last_modified=last_modified
        )

        assert obj.key == "test.txt"
        assert obj.content_type is None

    def test_object_list_response_empty(self):
        """Test ObjectListResponse with empty list."""
        response = ObjectListResponse(objects=[])
        assert response.objects == []
        assert response.prefix is None

    def test_object_list_response_with_prefix(self):
        """Test ObjectListResponse with prefix filter."""
        response = ObjectListResponse(objects=[], prefix="documents/")
        assert response.objects == []
        assert response.prefix == "documents/"

    def test_object_upload_request_minimal(self):
        """Test ObjectUploadRequest with minimal data."""
        request = ObjectUploadRequest(key="test.txt")
        assert request.key == "test.txt"
        assert request.content_type is None
        assert request.metadata is None

    def test_object_upload_request_complete(self):
        """Test ObjectUploadRequest with all fields."""
        metadata = {"author": "John Doe", "version": "1.0"}
        request = ObjectUploadRequest(
            key="test.txt", content_type="text/plain", metadata=metadata
        )

        assert request.key == "test.txt"
        assert request.content_type == "text/plain"
        assert request.metadata == metadata

    def test_object_upload_response(self):
        """Test ObjectUploadResponse."""
        response = ObjectUploadResponse(
            bucket="test-bucket", key="test.txt", size=1024, etag="abc123"
        )

        assert response.bucket == "test-bucket"
        assert response.key == "test.txt"
        assert response.size == 1024
        assert response.etag == "abc123"

    def test_object_metadata_response(self):
        """Test ObjectMetadataResponse."""
        last_modified = datetime(2023, 1, 1, 12, 0, 0)
        metadata = {"custom": "value"}

        response = ObjectMetadataResponse(
            key="test.txt",
            size=1024,
            content_type="text/plain",
            last_modified=last_modified,
            etag="abc123",
            metadata=metadata,
        )

        assert response.key == "test.txt"
        assert response.size == 1024
        assert response.content_type == "text/plain"
        assert response.last_modified == last_modified
        assert response.etag == "abc123"
        assert response.metadata == metadata


class TestPresignedUrlModels:
    """Test presigned URL-related models."""

    def test_presigned_url_request_default(self):
        """Test PresignedUrlRequest with default expiration."""
        request = PresignedUrlRequest()
        assert request.expires_in == 3600

    def test_presigned_url_request_custom(self):
        """Test PresignedUrlRequest with custom expiration."""
        request = PresignedUrlRequest(expires_in=7200)
        assert request.expires_in == 7200

    def test_presigned_url_request_validation_min(self):
        """Test PresignedUrlRequest minimum validation."""
        with pytest.raises(ValidationError):
            PresignedUrlRequest(expires_in=0)  # Below minimum

    def test_presigned_url_request_validation_max(self):
        """Test PresignedUrlRequest maximum validation."""
        with pytest.raises(ValidationError):
            PresignedUrlRequest(expires_in=604801)  # Above maximum

    def test_presigned_url_response(self):
        """Test PresignedUrlResponse."""
        response = PresignedUrlResponse(
            url="https://example.com/presigned-url", expires_in=3600
        )

        assert response.url == "https://example.com/presigned-url"
        assert response.expires_in == 3600


class TestErrorModel:
    """Test error response model."""

    def test_error_response_minimal(self):
        """Test ErrorResponse with minimal data."""
        error = ErrorResponse(error="Something went wrong")
        assert error.error == "Something went wrong"
        assert error.detail is None

    def test_error_response_with_detail(self):
        """Test ErrorResponse with detail."""
        error = ErrorResponse(
            error="Validation failed", detail="The bucket name is invalid"
        )

        assert error.error == "Validation failed"
        assert error.detail == "The bucket name is invalid"
