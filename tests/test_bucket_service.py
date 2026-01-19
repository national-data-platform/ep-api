# tests/test_bucket_service.py
"""
Tests for bucket service functions.
"""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime
from minio.error import S3Error

from api.services.minio_services.bucket_service import (
    create_bucket,
    list_buckets,
    get_bucket_info,
    delete_bucket,
    create_s3_error,
)
from api.models.minio_models import BucketInfo


class TestCreateS3Error:
    """Test cases for create_s3_error helper function."""

    def test_creates_s3_error_with_message_and_code(self):
        """Test that create_s3_error creates a properly formatted S3Error."""
        error = create_s3_error("Test message", "TestCode")

        assert isinstance(error, S3Error)
        assert "TestCode" in str(error)
        assert "Test message" in str(error)

    def test_creates_s3_error_with_response_attributes(self):
        """Test that S3Error has proper response attributes."""
        error = create_s3_error("Test message", "TestCode")

        # Should not raise any attribute errors
        assert error._code == "TestCode"
        assert error._message == "Test message"


class TestCreateBucket:
    """Test cases for create_bucket function."""

    @pytest.mark.asyncio
    @patch("api.services.minio_services.bucket_service.minio_client")
    async def test_create_bucket_success(self, mock_minio_client):
        """Test successful bucket creation."""
        mock_client = MagicMock()
        mock_client.bucket_exists.return_value = False
        mock_client.make_bucket.return_value = None
        mock_minio_client.client = mock_client

        result = await create_bucket("test-bucket")

        assert result is True
        mock_client.bucket_exists.assert_called_once_with("test-bucket")
        mock_client.make_bucket.assert_called_once_with("test-bucket", location=None)

    @pytest.mark.asyncio
    @patch("api.services.minio_services.bucket_service.minio_client")
    async def test_create_bucket_with_region(self, mock_minio_client):
        """Test bucket creation with region."""
        mock_client = MagicMock()
        mock_client.bucket_exists.return_value = False
        mock_client.make_bucket.return_value = None
        mock_minio_client.client = mock_client

        result = await create_bucket("test-bucket", region="us-east-1")

        assert result is True
        mock_client.make_bucket.assert_called_once_with(
            "test-bucket", location="us-east-1"
        )

    @pytest.mark.asyncio
    @patch("api.services.minio_services.bucket_service.minio_client")
    async def test_create_bucket_already_exists(self, mock_minio_client):
        """Test creating a bucket that already exists."""
        mock_client = MagicMock()
        mock_client.bucket_exists.return_value = True
        mock_minio_client.client = mock_client

        with pytest.raises(S3Error) as exc_info:
            await create_bucket("existing-bucket")

        assert "already exists" in str(exc_info.value)
        mock_client.make_bucket.assert_not_called()

    @pytest.mark.asyncio
    @patch("api.services.minio_services.bucket_service.minio_client")
    async def test_create_bucket_s3_error(self, mock_minio_client):
        """Test bucket creation with S3Error."""
        mock_client = MagicMock()
        mock_client.bucket_exists.return_value = False
        mock_client.make_bucket.side_effect = create_s3_error(
            "Access denied", "AccessDenied"
        )
        mock_minio_client.client = mock_client

        with pytest.raises(S3Error) as exc_info:
            await create_bucket("test-bucket")

        assert "AccessDenied" in str(exc_info.value)

    @pytest.mark.asyncio
    @patch("api.services.minio_services.bucket_service.minio_client")
    async def test_create_bucket_unexpected_error(self, mock_minio_client):
        """Test bucket creation with unexpected error."""
        mock_client = MagicMock()
        mock_client.bucket_exists.return_value = False
        mock_client.make_bucket.side_effect = Exception("Unexpected error")
        mock_minio_client.client = mock_client

        with pytest.raises(S3Error) as exc_info:
            await create_bucket("test-bucket")

        assert "InternalError" in str(exc_info.value)


class TestListBuckets:
    """Test cases for list_buckets function."""

    @pytest.mark.asyncio
    @patch("api.services.minio_services.bucket_service.minio_client")
    async def test_list_buckets_success(self, mock_minio_client):
        """Test successful bucket listing."""
        mock_bucket1 = MagicMock()
        mock_bucket1.name = "bucket-1"
        mock_bucket1.creation_date = datetime(2024, 1, 1)

        mock_bucket2 = MagicMock()
        mock_bucket2.name = "bucket-2"
        mock_bucket2.creation_date = datetime(2024, 1, 2)

        mock_client = MagicMock()
        mock_client.list_buckets.return_value = [mock_bucket1, mock_bucket2]
        mock_minio_client.client = mock_client

        result = await list_buckets()

        assert len(result.buckets) == 2
        assert result.buckets[0].name == "bucket-1"
        assert result.buckets[1].name == "bucket-2"
        assert result.buckets[0].creation_date == datetime(2024, 1, 1)

    @pytest.mark.asyncio
    @patch("api.services.minio_services.bucket_service.minio_client")
    async def test_list_buckets_empty(self, mock_minio_client):
        """Test listing buckets when there are none."""
        mock_client = MagicMock()
        mock_client.list_buckets.return_value = []
        mock_minio_client.client = mock_client

        result = await list_buckets()

        assert len(result.buckets) == 0

    @pytest.mark.asyncio
    @patch("api.services.minio_services.bucket_service.minio_client")
    async def test_list_buckets_s3_error(self, mock_minio_client):
        """Test listing buckets with S3Error."""
        mock_client = MagicMock()
        mock_client.list_buckets.side_effect = create_s3_error(
            "Access denied", "AccessDenied"
        )
        mock_minio_client.client = mock_client

        with pytest.raises(S3Error) as exc_info:
            await list_buckets()

        assert "AccessDenied" in str(exc_info.value)

    @pytest.mark.asyncio
    @patch("api.services.minio_services.bucket_service.minio_client")
    async def test_list_buckets_unexpected_error(self, mock_minio_client):
        """Test listing buckets with unexpected error."""
        mock_client = MagicMock()
        mock_client.list_buckets.side_effect = Exception("Network error")
        mock_minio_client.client = mock_client

        with pytest.raises(S3Error) as exc_info:
            await list_buckets()

        assert "InternalError" in str(exc_info.value)


class TestGetBucketInfo:
    """Test cases for get_bucket_info function."""

    @pytest.mark.asyncio
    @patch("api.services.minio_services.bucket_service.minio_client")
    async def test_get_bucket_info_success(self, mock_minio_client):
        """Test getting bucket info successfully."""
        mock_bucket = MagicMock()
        mock_bucket.name = "test-bucket"
        mock_bucket.creation_date = datetime(2024, 1, 1)

        mock_client = MagicMock()
        mock_client.bucket_exists.return_value = True
        mock_client.list_buckets.return_value = [mock_bucket]
        mock_minio_client.client = mock_client

        result = await get_bucket_info("test-bucket")

        assert result.name == "test-bucket"
        assert result.creation_date == datetime(2024, 1, 1)

    @pytest.mark.asyncio
    @patch("api.services.minio_services.bucket_service.minio_client")
    async def test_get_bucket_info_not_exists(self, mock_minio_client):
        """Test getting info for non-existent bucket."""
        mock_client = MagicMock()
        mock_client.bucket_exists.return_value = False
        mock_minio_client.client = mock_client

        with pytest.raises(S3Error) as exc_info:
            await get_bucket_info("nonexistent-bucket")

        assert "does not exist" in str(exc_info.value)

    @pytest.mark.asyncio
    @patch("api.services.minio_services.bucket_service.minio_client")
    async def test_get_bucket_info_not_in_list(self, mock_minio_client):
        """Test getting bucket info when bucket exists but not in list."""
        mock_other_bucket = MagicMock()
        mock_other_bucket.name = "other-bucket"
        mock_other_bucket.creation_date = datetime(2024, 1, 1)

        mock_client = MagicMock()
        mock_client.bucket_exists.return_value = True
        mock_client.list_buckets.return_value = [mock_other_bucket]
        mock_minio_client.client = mock_client

        result = await get_bucket_info("test-bucket")

        assert result.name == "test-bucket"
        assert result.creation_date is None

    @pytest.mark.asyncio
    @patch("api.services.minio_services.bucket_service.minio_client")
    async def test_get_bucket_info_s3_error(self, mock_minio_client):
        """Test getting bucket info with S3Error."""
        mock_client = MagicMock()
        mock_client.bucket_exists.side_effect = create_s3_error(
            "Access denied", "AccessDenied"
        )
        mock_minio_client.client = mock_client

        with pytest.raises(S3Error) as exc_info:
            await get_bucket_info("test-bucket")

        assert "AccessDenied" in str(exc_info.value)

    @pytest.mark.asyncio
    @patch("api.services.minio_services.bucket_service.minio_client")
    async def test_get_bucket_info_unexpected_error(self, mock_minio_client):
        """Test getting bucket info with unexpected error."""
        mock_client = MagicMock()
        mock_client.bucket_exists.return_value = True
        mock_client.list_buckets.side_effect = Exception("Unexpected error")
        mock_minio_client.client = mock_client

        with pytest.raises(S3Error) as exc_info:
            await get_bucket_info("test-bucket")

        assert "InternalError" in str(exc_info.value)


class TestDeleteBucket:
    """Test cases for delete_bucket function."""

    @pytest.mark.asyncio
    @patch("api.services.minio_services.bucket_service.minio_client")
    async def test_delete_bucket_success(self, mock_minio_client):
        """Test successful bucket deletion."""
        mock_client = MagicMock()
        mock_client.bucket_exists.return_value = True
        mock_client.list_objects.return_value = []
        mock_client.remove_bucket.return_value = None
        mock_minio_client.client = mock_client

        result = await delete_bucket("test-bucket")

        assert result is True
        mock_client.bucket_exists.assert_called_once_with("test-bucket")
        mock_client.list_objects.assert_called_once_with("test-bucket", recursive=True)
        mock_client.remove_bucket.assert_called_once_with("test-bucket")

    @pytest.mark.asyncio
    @patch("api.services.minio_services.bucket_service.minio_client")
    async def test_delete_bucket_not_exists(self, mock_minio_client):
        """Test deleting non-existent bucket."""
        mock_client = MagicMock()
        mock_client.bucket_exists.return_value = False
        mock_minio_client.client = mock_client

        with pytest.raises(S3Error) as exc_info:
            await delete_bucket("nonexistent-bucket")

        assert "does not exist" in str(exc_info.value)
        mock_client.remove_bucket.assert_not_called()

    @pytest.mark.asyncio
    @patch("api.services.minio_services.bucket_service.minio_client")
    async def test_delete_bucket_not_empty(self, mock_minio_client):
        """Test deleting bucket that is not empty."""
        mock_object = MagicMock()
        mock_object.object_name = "file.txt"

        mock_client = MagicMock()
        mock_client.bucket_exists.return_value = True
        mock_client.list_objects.return_value = [mock_object]
        mock_minio_client.client = mock_client

        with pytest.raises(S3Error) as exc_info:
            await delete_bucket("test-bucket")

        assert "not empty" in str(exc_info.value)
        mock_client.remove_bucket.assert_not_called()

    @pytest.mark.asyncio
    @patch("api.services.minio_services.bucket_service.minio_client")
    async def test_delete_bucket_s3_error(self, mock_minio_client):
        """Test deleting bucket with S3Error."""
        mock_client = MagicMock()
        mock_client.bucket_exists.return_value = True
        mock_client.list_objects.return_value = []
        mock_client.remove_bucket.side_effect = create_s3_error(
            "Access denied", "AccessDenied"
        )
        mock_minio_client.client = mock_client

        with pytest.raises(S3Error) as exc_info:
            await delete_bucket("test-bucket")

        assert "AccessDenied" in str(exc_info.value)

    @pytest.mark.asyncio
    @patch("api.services.minio_services.bucket_service.minio_client")
    async def test_delete_bucket_unexpected_error(self, mock_minio_client):
        """Test deleting bucket with unexpected error."""
        mock_client = MagicMock()
        mock_client.bucket_exists.return_value = True
        mock_client.list_objects.side_effect = Exception("Network error")
        mock_minio_client.client = mock_client

        with pytest.raises(S3Error) as exc_info:
            await delete_bucket("test-bucket")

        assert "InternalError" in str(exc_info.value)
