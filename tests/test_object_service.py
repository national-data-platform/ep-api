# tests/test_object_service.py
"""
Tests for object service functions.
"""
import pytest
from unittest.mock import MagicMock, patch, Mock
from datetime import datetime, timedelta
from io import BytesIO
from minio.error import S3Error

from api.services.minio_services.object_service import (
    upload_object,
    list_objects,
    get_object_metadata,
    delete_object,
    generate_presigned_upload_url,
    generate_presigned_download_url,
    create_s3_error,
)


class TestCreateS3Error:
    """Test cases for create_s3_error helper function."""

    def test_creates_s3_error_with_message_and_code(self):
        """Test that create_s3_error creates a properly formatted S3Error."""
        error = create_s3_error("Test message", "TestCode")

        assert isinstance(error, S3Error)
        assert "TestCode" in str(error)
        assert "Test message" in str(error)


class TestUploadObject:
    """Test cases for upload_object function."""

    @pytest.mark.asyncio
    @patch("api.services.minio_services.object_service.minio_client")
    async def test_upload_object_success(self, mock_minio_client):
        """Test successful object upload."""
        file_data = BytesIO(b"test data content")

        mock_result = MagicMock()
        mock_result.etag = "etag123"

        mock_stat = MagicMock()
        mock_stat.size = 17

        mock_client = MagicMock()
        mock_client.bucket_exists.return_value = True
        mock_client.put_object.return_value = mock_result
        mock_client.stat_object.return_value = mock_stat
        mock_minio_client.client = mock_client

        result = await upload_object("test-bucket", "test.txt", file_data)

        assert result.bucket == "test-bucket"
        assert result.key == "test.txt"
        assert result.size == 17
        assert result.etag == "etag123"
        mock_client.put_object.assert_called_once()

    @pytest.mark.asyncio
    @patch("api.services.minio_services.object_service.minio_client")
    async def test_upload_object_with_metadata(self, mock_minio_client):
        """Test uploading object with metadata and content type."""
        file_data = BytesIO(b"test")

        mock_result = MagicMock()
        mock_result.etag = "etag456"

        mock_stat = MagicMock()
        mock_stat.size = 4

        mock_client = MagicMock()
        mock_client.bucket_exists.return_value = True
        mock_client.put_object.return_value = mock_result
        mock_client.stat_object.return_value = mock_stat
        mock_minio_client.client = mock_client

        result = await upload_object(
            "test-bucket",
            "test.txt",
            file_data,
            content_type="text/plain",
            metadata={"author": "test"}
        )

        assert result.size == 4
        call_args = mock_client.put_object.call_args
        assert call_args[1]["content_type"] == "text/plain"
        assert call_args[1]["metadata"] == {"author": "test"}

    @pytest.mark.asyncio
    @patch("api.services.minio_services.object_service.minio_client")
    async def test_upload_object_bucket_not_exists(self, mock_minio_client):
        """Test uploading to non-existent bucket."""
        file_data = BytesIO(b"test")

        mock_client = MagicMock()
        mock_client.bucket_exists.return_value = False
        mock_minio_client.client = mock_client

        with pytest.raises(S3Error) as exc_info:
            await upload_object("nonexistent-bucket", "test.txt", file_data)

        assert "does not exist" in str(exc_info.value)

    @pytest.mark.asyncio
    @patch("api.services.minio_services.object_service.minio_client")
    async def test_upload_object_s3_error(self, mock_minio_client):
        """Test upload with S3Error."""
        file_data = BytesIO(b"test")

        mock_client = MagicMock()
        mock_client.bucket_exists.return_value = True
        mock_client.put_object.side_effect = create_s3_error("Access denied", "AccessDenied")
        mock_minio_client.client = mock_client

        with pytest.raises(S3Error) as exc_info:
            await upload_object("test-bucket", "test.txt", file_data)

        assert "AccessDenied" in str(exc_info.value)

    @pytest.mark.asyncio
    @patch("api.services.minio_services.object_service.minio_client")
    async def test_upload_object_unexpected_error(self, mock_minio_client):
        """Test upload with unexpected error."""
        file_data = BytesIO(b"test")

        mock_client = MagicMock()
        mock_client.bucket_exists.return_value = True
        mock_client.put_object.side_effect = Exception("Network error")
        mock_minio_client.client = mock_client

        with pytest.raises(S3Error) as exc_info:
            await upload_object("test-bucket", "test.txt", file_data)

        assert "InternalError" in str(exc_info.value)


class TestListObjects:
    """Test cases for list_objects function."""

    @pytest.mark.asyncio
    @patch("api.services.minio_services.object_service.minio_client")
    async def test_list_objects_success(self, mock_minio_client):
        """Test successful object listing."""
        mock_obj1 = MagicMock()
        mock_obj1.object_name = "file1.txt"
        mock_obj1.size = 100
        mock_obj1.etag = "etag1"
        mock_obj1.last_modified = datetime(2024, 1, 1)

        mock_obj2 = MagicMock()
        mock_obj2.object_name = "file2.txt"
        mock_obj2.size = 200
        mock_obj2.etag = "etag2"
        mock_obj2.last_modified = datetime(2024, 1, 2)

        mock_client = MagicMock()
        mock_client.bucket_exists.return_value = True
        mock_client.list_objects.return_value = [mock_obj1, mock_obj2]
        mock_minio_client.client = mock_client

        result = await list_objects("test-bucket")

        assert len(result.objects) == 2
        assert result.objects[0].key == "file1.txt"
        assert result.objects[0].size == 100
        assert result.objects[1].key == "file2.txt"
        assert result.prefix is None

    @pytest.mark.asyncio
    @patch("api.services.minio_services.object_service.minio_client")
    async def test_list_objects_with_prefix(self, mock_minio_client):
        """Test listing objects with prefix filter."""
        mock_obj = MagicMock()
        mock_obj.object_name = "folder/file.txt"
        mock_obj.size = 100
        mock_obj.etag = "etag1"
        mock_obj.last_modified = datetime(2024, 1, 1)

        mock_client = MagicMock()
        mock_client.bucket_exists.return_value = True
        mock_client.list_objects.return_value = [mock_obj]
        mock_minio_client.client = mock_client

        result = await list_objects("test-bucket", prefix="folder/")

        assert len(result.objects) == 1
        assert result.objects[0].key == "folder/file.txt"
        assert result.prefix == "folder/"
        mock_client.list_objects.assert_called_with("test-bucket", prefix="folder/", recursive=True)

    @pytest.mark.asyncio
    @patch("api.services.minio_services.object_service.minio_client")
    async def test_list_objects_empty(self, mock_minio_client):
        """Test listing objects when bucket is empty."""
        mock_client = MagicMock()
        mock_client.bucket_exists.return_value = True
        mock_client.list_objects.return_value = []
        mock_minio_client.client = mock_client

        result = await list_objects("test-bucket")

        assert len(result.objects) == 0

    @pytest.mark.asyncio
    @patch("api.services.minio_services.object_service.minio_client")
    async def test_list_objects_bucket_not_exists(self, mock_minio_client):
        """Test listing objects from non-existent bucket."""
        mock_client = MagicMock()
        mock_client.bucket_exists.return_value = False
        mock_minio_client.client = mock_client

        with pytest.raises(S3Error) as exc_info:
            await list_objects("nonexistent-bucket")

        assert "does not exist" in str(exc_info.value)

    @pytest.mark.asyncio
    @patch("api.services.minio_services.object_service.minio_client")
    async def test_list_objects_s3_error(self, mock_minio_client):
        """Test listing objects with S3Error."""
        mock_client = MagicMock()
        mock_client.bucket_exists.return_value = True
        mock_client.list_objects.side_effect = create_s3_error("Access denied", "AccessDenied")
        mock_minio_client.client = mock_client

        with pytest.raises(S3Error) as exc_info:
            await list_objects("test-bucket")

        assert "AccessDenied" in str(exc_info.value)

    @pytest.mark.asyncio
    @patch("api.services.minio_services.object_service.minio_client")
    async def test_list_objects_unexpected_error(self, mock_minio_client):
        """Test listing objects with unexpected error."""
        mock_client = MagicMock()
        mock_client.bucket_exists.return_value = True
        mock_client.list_objects.side_effect = Exception("Network error")
        mock_minio_client.client = mock_client

        with pytest.raises(S3Error) as exc_info:
            await list_objects("test-bucket")

        assert "InternalError" in str(exc_info.value)


class TestGetObjectMetadata:
    """Test cases for get_object_metadata function."""

    @pytest.mark.asyncio
    @patch("api.services.minio_services.object_service.minio_client")
    async def test_get_object_metadata_success(self, mock_minio_client):
        """Test getting object metadata successfully."""
        mock_stat = MagicMock()
        mock_stat.size = 1024
        mock_stat.content_type = "text/plain"
        mock_stat.last_modified = datetime(2024, 1, 1)
        mock_stat.etag = "etag123"
        mock_stat.metadata = {"author": "test"}

        mock_client = MagicMock()
        mock_client.stat_object.return_value = mock_stat
        mock_minio_client.client = mock_client

        result = await get_object_metadata("test-bucket", "test.txt")

        assert result.key == "test.txt"
        assert result.size == 1024
        assert result.content_type == "text/plain"
        assert result.etag == "etag123"
        assert result.metadata == {"author": "test"}

    @pytest.mark.asyncio
    @patch("api.services.minio_services.object_service.minio_client")
    async def test_get_object_metadata_no_content_type(self, mock_minio_client):
        """Test getting metadata when content_type is None."""
        mock_stat = MagicMock()
        mock_stat.size = 1024
        mock_stat.content_type = None
        mock_stat.last_modified = datetime(2024, 1, 1)
        mock_stat.etag = "etag123"
        mock_stat.metadata = None

        mock_client = MagicMock()
        mock_client.stat_object.return_value = mock_stat
        mock_minio_client.client = mock_client

        result = await get_object_metadata("test-bucket", "test.txt")

        assert result.content_type == "application/octet-stream"
        assert result.metadata == {}

    @pytest.mark.asyncio
    @patch("api.services.minio_services.object_service.minio_client")
    async def test_get_object_metadata_s3_error(self, mock_minio_client):
        """Test getting metadata with S3Error."""
        mock_client = MagicMock()
        mock_client.stat_object.side_effect = create_s3_error("Not found", "NoSuchKey")
        mock_minio_client.client = mock_client

        with pytest.raises(S3Error) as exc_info:
            await get_object_metadata("test-bucket", "test.txt")

        assert "NoSuchKey" in str(exc_info.value)

    @pytest.mark.asyncio
    @patch("api.services.minio_services.object_service.minio_client")
    async def test_get_object_metadata_unexpected_error(self, mock_minio_client):
        """Test getting metadata with unexpected error."""
        mock_client = MagicMock()
        mock_client.stat_object.side_effect = Exception("Network error")
        mock_minio_client.client = mock_client

        with pytest.raises(S3Error) as exc_info:
            await get_object_metadata("test-bucket", "test.txt")

        assert "InternalError" in str(exc_info.value)


class TestDeleteObject:
    """Test cases for delete_object function."""

    @pytest.mark.asyncio
    @patch("api.services.minio_services.object_service.minio_client")
    async def test_delete_object_success(self, mock_minio_client):
        """Test successful object deletion."""
        mock_stat = MagicMock()

        mock_client = MagicMock()
        mock_client.stat_object.return_value = mock_stat
        mock_client.remove_object.return_value = None
        mock_minio_client.client = mock_client

        result = await delete_object("test-bucket", "test.txt")

        assert result is True
        mock_client.stat_object.assert_called_once_with("test-bucket", "test.txt")
        mock_client.remove_object.assert_called_once_with("test-bucket", "test.txt")

    @pytest.mark.asyncio
    @patch("api.services.minio_services.object_service.minio_client")
    async def test_delete_object_not_exists(self, mock_minio_client):
        """Test deleting non-existent object."""
        mock_client = MagicMock()
        mock_client.stat_object.side_effect = create_s3_error("Not found", "NoSuchKey")
        mock_minio_client.client = mock_client

        with pytest.raises(S3Error) as exc_info:
            await delete_object("test-bucket", "nonexistent.txt")

        assert "does not exist" in str(exc_info.value)
        mock_client.remove_object.assert_not_called()

    @pytest.mark.asyncio
    @patch("api.services.minio_services.object_service.minio_client")
    async def test_delete_object_s3_error(self, mock_minio_client):
        """Test deleting object with S3Error."""
        mock_stat = MagicMock()

        mock_client = MagicMock()
        mock_client.stat_object.return_value = mock_stat
        mock_client.remove_object.side_effect = create_s3_error("Access denied", "AccessDenied")
        mock_minio_client.client = mock_client

        with pytest.raises(S3Error) as exc_info:
            await delete_object("test-bucket", "test.txt")

        assert "AccessDenied" in str(exc_info.value)

    @pytest.mark.asyncio
    @patch("api.services.minio_services.object_service.minio_client")
    async def test_delete_object_unexpected_error(self, mock_minio_client):
        """Test deleting object with unexpected error."""
        mock_client = MagicMock()
        mock_client.stat_object.side_effect = Exception("Network error")
        mock_minio_client.client = mock_client

        with pytest.raises(S3Error) as exc_info:
            await delete_object("test-bucket", "test.txt")

        assert "InternalError" in str(exc_info.value)


class TestGeneratePresignedUploadUrl:
    """Test cases for generate_presigned_upload_url function."""

    @pytest.mark.asyncio
    @patch("api.services.minio_services.object_service.minio_client")
    async def test_generate_presigned_upload_url_success(self, mock_minio_client):
        """Test generating presigned upload URL successfully."""
        mock_client = MagicMock()
        mock_client.bucket_exists.return_value = True
        mock_client.presigned_put_object.return_value = "https://presigned-url.com/upload"
        mock_minio_client.client = mock_client

        result = await generate_presigned_upload_url("test-bucket", "test.txt")

        assert result.url == "https://presigned-url.com/upload"
        assert result.expires_in == 3600
        mock_client.presigned_put_object.assert_called_once()

    @pytest.mark.asyncio
    @patch("api.services.minio_services.object_service.minio_client")
    async def test_generate_presigned_upload_url_custom_expiry(self, mock_minio_client):
        """Test generating presigned URL with custom expiry time."""
        mock_client = MagicMock()
        mock_client.bucket_exists.return_value = True
        mock_client.presigned_put_object.return_value = "https://presigned-url.com/upload"
        mock_minio_client.client = mock_client

        result = await generate_presigned_upload_url("test-bucket", "test.txt", expires_in=7200)

        assert result.expires_in == 7200
        call_args = mock_client.presigned_put_object.call_args
        assert call_args[1]["expires"] == timedelta(seconds=7200)

    @pytest.mark.asyncio
    @patch("api.services.minio_services.object_service.minio_client")
    async def test_generate_presigned_upload_url_bucket_not_exists(self, mock_minio_client):
        """Test generating URL for non-existent bucket."""
        mock_client = MagicMock()
        mock_client.bucket_exists.return_value = False
        mock_minio_client.client = mock_client

        with pytest.raises(S3Error) as exc_info:
            await generate_presigned_upload_url("nonexistent-bucket", "test.txt")

        assert "does not exist" in str(exc_info.value)

    @pytest.mark.asyncio
    @patch("api.services.minio_services.object_service.minio_client")
    async def test_generate_presigned_upload_url_s3_error(self, mock_minio_client):
        """Test generating URL with S3Error."""
        mock_client = MagicMock()
        mock_client.bucket_exists.return_value = True
        mock_client.presigned_put_object.side_effect = create_s3_error("Access denied", "AccessDenied")
        mock_minio_client.client = mock_client

        with pytest.raises(S3Error) as exc_info:
            await generate_presigned_upload_url("test-bucket", "test.txt")

        assert "AccessDenied" in str(exc_info.value)

    @pytest.mark.asyncio
    @patch("api.services.minio_services.object_service.minio_client")
    async def test_generate_presigned_upload_url_unexpected_error(self, mock_minio_client):
        """Test generating URL with unexpected error."""
        mock_client = MagicMock()
        mock_client.bucket_exists.return_value = True
        mock_client.presigned_put_object.side_effect = Exception("Network error")
        mock_minio_client.client = mock_client

        with pytest.raises(S3Error) as exc_info:
            await generate_presigned_upload_url("test-bucket", "test.txt")

        assert "InternalError" in str(exc_info.value)


class TestGeneratePresignedDownloadUrl:
    """Test cases for generate_presigned_download_url function."""

    @pytest.mark.asyncio
    @patch("api.services.minio_services.object_service.minio_client")
    async def test_generate_presigned_download_url_success(self, mock_minio_client):
        """Test generating presigned download URL successfully."""
        mock_stat = MagicMock()

        mock_client = MagicMock()
        mock_client.stat_object.return_value = mock_stat
        mock_client.presigned_get_object.return_value = "https://presigned-url.com/download"
        mock_minio_client.client = mock_client

        result = await generate_presigned_download_url("test-bucket", "test.txt")

        assert result.url == "https://presigned-url.com/download"
        assert result.expires_in == 3600
        mock_client.stat_object.assert_called_once_with("test-bucket", "test.txt")

    @pytest.mark.asyncio
    @patch("api.services.minio_services.object_service.minio_client")
    async def test_generate_presigned_download_url_custom_expiry(self, mock_minio_client):
        """Test generating download URL with custom expiry time."""
        mock_stat = MagicMock()

        mock_client = MagicMock()
        mock_client.stat_object.return_value = mock_stat
        mock_client.presigned_get_object.return_value = "https://presigned-url.com/download"
        mock_minio_client.client = mock_client

        result = await generate_presigned_download_url("test-bucket", "test.txt", expires_in=1800)

        assert result.expires_in == 1800
        call_args = mock_client.presigned_get_object.call_args
        assert call_args[1]["expires"] == timedelta(seconds=1800)

    @pytest.mark.asyncio
    @patch("api.services.minio_services.object_service.minio_client")
    async def test_generate_presigned_download_url_object_not_exists(self, mock_minio_client):
        """Test generating download URL for non-existent object."""
        mock_client = MagicMock()
        mock_client.stat_object.side_effect = create_s3_error("Not found", "NoSuchKey")
        mock_minio_client.client = mock_client

        with pytest.raises(S3Error) as exc_info:
            await generate_presigned_download_url("test-bucket", "nonexistent.txt")

        assert "does not exist" in str(exc_info.value)

    @pytest.mark.asyncio
    @patch("api.services.minio_services.object_service.minio_client")
    async def test_generate_presigned_download_url_s3_error(self, mock_minio_client):
        """Test generating download URL with S3Error."""
        mock_stat = MagicMock()

        mock_client = MagicMock()
        mock_client.stat_object.return_value = mock_stat
        mock_client.presigned_get_object.side_effect = create_s3_error("Access denied", "AccessDenied")
        mock_minio_client.client = mock_client

        with pytest.raises(S3Error) as exc_info:
            await generate_presigned_download_url("test-bucket", "test.txt")

        assert "AccessDenied" in str(exc_info.value)

    @pytest.mark.asyncio
    @patch("api.services.minio_services.object_service.minio_client")
    async def test_generate_presigned_download_url_unexpected_error(self, mock_minio_client):
        """Test generating download URL with unexpected error."""
        mock_client = MagicMock()
        mock_client.stat_object.side_effect = Exception("Network error")
        mock_minio_client.client = mock_client

        with pytest.raises(S3Error) as exc_info:
            await generate_presigned_download_url("test-bucket", "test.txt")

        assert "InternalError" in str(exc_info.value)
