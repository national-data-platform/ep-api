import pytest
from unittest.mock import Mock, patch, MagicMock
from minio.error import S3Error
from datetime import datetime
import io

from api.services.minio_services import bucket_service, object_service
from api.services.minio_services.minio_client import minio_client
from api.models.minio_models import BucketInfo, BucketListResponse

# Mock S3Error class that inherits from S3Error 
class MockS3Error(S3Error):
    def __init__(self, message, code):
        # Create a minimal mock response
        mock_response = Mock()
        mock_response.status = 400
        mock_response.data = b""
        mock_response.headers = {}
        
        # Call parent constructor with required parameters  
        super().__init__(code, message, "resource", "request_id", "host_id", mock_response)

# Helper function to create S3Error mocks
def create_s3_error_mock(message, code):
    return MockS3Error(message, code)


class TestMinioClient:
    """Test S3 client functionality."""
    
    def test_minio_client_not_configured(self):
        """Test MINIO client when not configured."""
        with patch('api.services.minio_services.minio_client.s3_settings') as mock_settings:
            mock_settings.is_configured = False
            
            with pytest.raises(ValueError, match="S3 is not properly configured"):
                _ = minio_client.client
    
    @patch('api.services.minio_services.minio_client.Minio')
    def test_minio_client_initialization(self, mock_minio_class):
        """Test successful MINIO client initialization."""
        mock_minio_instance = Mock()
        mock_minio_class.return_value = mock_minio_instance
        
        with patch('api.services.minio_services.minio_client.s3_settings') as mock_settings:
            mock_settings.is_configured = True
            mock_settings.endpoint = "localhost:9000"
            mock_settings.access_key = "access"
            mock_settings.secret_key = "secret"
            mock_settings.secure = False
            mock_settings.region = "us-east-1"
            
            # Reset client to None to force re-initialization
            minio_client._client = None
            
            client = minio_client.client
            
            assert client == mock_minio_instance
            mock_minio_class.assert_called_once_with(
                endpoint="localhost:9000",
                access_key="access",
                secret_key="secret",
                secure=False,
                region="us-east-1"
            )
    
    def test_minio_test_connection_success(self):
        """Test successful connection test."""
        with patch.object(minio_client, '_client') as mock_client:
            mock_client.list_buckets.return_value = []
            
            result = minio_client.test_connection()
            
            assert result is True
            mock_client.list_buckets.assert_called_once()
    
    def test_minio_test_connection_s3_error(self):
        """Test connection test with S3 error."""
        with patch.object(minio_client, '_client') as mock_client:
            mock_client.list_buckets.side_effect = create_s3_error_mock("Access denied", "AccessDenied")
            
            result = minio_client.test_connection()
            
            assert result is False
    
    def test_minio_test_connection_general_error(self):
        """Test connection test with general error."""
        with patch.object(minio_client, '_client') as mock_client:
            mock_client.list_buckets.side_effect = Exception("Network error")
            
            result = minio_client.test_connection()
            
            assert result is False


class TestBucketService:
    """Test bucket service functionality."""
    
    @pytest.mark.asyncio
    async def test_create_bucket_success(self):
        """Test successful bucket creation."""
        with patch('api.services.minio_services.bucket_service.minio_client') as mock_client:
            mock_client.client.bucket_exists.return_value = False
            mock_client.client.make_bucket.return_value = None
            
            result = await bucket_service.create_bucket("test-bucket")
            
            assert result is True
            mock_client.client.bucket_exists.assert_called_once_with("test-bucket")
            mock_client.client.make_bucket.assert_called_once_with("test-bucket", location=None)
    
    @pytest.mark.asyncio
    async def test_create_bucket_already_exists(self):
        """Test bucket creation when bucket already exists."""
        with patch('api.services.minio_services.bucket_service.minio_client') as mock_client:
            mock_client.client.bucket_exists.return_value = True
            
            with pytest.raises(S3Error, match="Bucket 'test-bucket' already exists"):
                await bucket_service.create_bucket("test-bucket")
    
    @pytest.mark.asyncio
    async def test_list_buckets_success(self):
        """Test successful bucket listing."""
        mock_bucket1 = Mock()
        mock_bucket1.name = "bucket1"
        mock_bucket1.creation_date = datetime(2023, 1, 1)
        
        mock_bucket2 = Mock()
        mock_bucket2.name = "bucket2"
        mock_bucket2.creation_date = datetime(2023, 1, 2)
        
        with patch('api.services.minio_services.bucket_service.minio_client') as mock_client:
            mock_client.client.list_buckets.return_value = [mock_bucket1, mock_bucket2]
            
            result = await bucket_service.list_buckets()
            
            assert isinstance(result, BucketListResponse)
            assert len(result.buckets) == 2
            assert result.buckets[0].name == "bucket1"
            assert result.buckets[1].name == "bucket2"
    
    @pytest.mark.asyncio
    async def test_get_bucket_info_success(self):
        """Test successful bucket info retrieval."""
        mock_bucket = Mock()
        mock_bucket.name = "test-bucket"
        mock_bucket.creation_date = datetime(2023, 1, 1)
        
        with patch('api.services.minio_services.bucket_service.minio_client') as mock_client:
            mock_client.client.bucket_exists.return_value = True
            mock_client.client.list_buckets.return_value = [mock_bucket]
            
            result = await bucket_service.get_bucket_info("test-bucket")
            
            assert isinstance(result, BucketInfo)
            assert result.name == "test-bucket"
            assert result.creation_date == datetime(2023, 1, 1)
    
    @pytest.mark.asyncio
    async def test_get_bucket_info_not_found(self):
        """Test bucket info retrieval for non-existent bucket."""
        with patch('api.services.minio_services.bucket_service.minio_client') as mock_client:
            mock_client.client.bucket_exists.return_value = False
            
            with pytest.raises(S3Error, match="Bucket 'test-bucket' does not exist"):
                await bucket_service.get_bucket_info("test-bucket")
    
    @pytest.mark.asyncio
    async def test_delete_bucket_success(self):
        """Test successful bucket deletion."""
        with patch('api.services.minio_services.bucket_service.minio_client') as mock_client:
            mock_client.client.bucket_exists.return_value = True
            mock_client.client.list_objects.return_value = []  # Empty bucket
            mock_client.client.remove_bucket.return_value = None
            
            result = await bucket_service.delete_bucket("test-bucket")
            
            assert result is True
            mock_client.client.remove_bucket.assert_called_once_with("test-bucket")
    
    @pytest.mark.asyncio
    async def test_delete_bucket_not_empty(self):
        """Test bucket deletion when bucket is not empty."""
        mock_object = Mock()
        
        with patch('api.services.minio_services.bucket_service.minio_client') as mock_client:
            mock_client.client.bucket_exists.return_value = True
            mock_client.client.list_objects.return_value = [mock_object]  # Non-empty bucket
            
            with pytest.raises(S3Error, match="Bucket 'test-bucket' is not empty"):
                await bucket_service.delete_bucket("test-bucket")


class TestObjectService:
    """Test object service functionality."""
    
    @pytest.mark.asyncio
    async def test_upload_object_success(self):
        """Test successful object upload."""
        file_data = io.BytesIO(b"test content")
        
        mock_result = Mock()
        mock_result.etag = "test-etag"
        
        mock_stat = Mock()
        mock_stat.size = 12
        
        with patch('api.services.minio_services.object_service.minio_client') as mock_client:
            mock_client.client.bucket_exists.return_value = True
            mock_client.client.put_object.return_value = mock_result
            mock_client.client.stat_object.return_value = mock_stat
            
            result = await object_service.upload_object(
                "test-bucket", "test-key", file_data, "text/plain"
            )
            
            assert result.bucket == "test-bucket"
            assert result.key == "test-key"
            assert result.size == 12
            assert result.etag == "test-etag"
    
    @pytest.mark.asyncio
    async def test_upload_object_bucket_not_found(self):
        """Test object upload to non-existent bucket."""
        file_data = io.BytesIO(b"test content")
        
        with patch('api.services.minio_services.object_service.minio_client') as mock_client:
            mock_client.client.bucket_exists.return_value = False
            
            with pytest.raises(S3Error, match="Bucket 'test-bucket' does not exist"):
                await object_service.upload_object("test-bucket", "test-key", file_data)
    
    @pytest.mark.asyncio
    async def test_list_objects_success(self):
        """Test successful object listing."""
        mock_obj1 = Mock()
        mock_obj1.object_name = "obj1"
        mock_obj1.size = 100
        mock_obj1.etag = "etag1"
        mock_obj1.last_modified = datetime(2023, 1, 1)
        
        mock_obj2 = Mock()
        mock_obj2.object_name = "obj2"
        mock_obj2.size = 200
        mock_obj2.etag = "etag2"
        mock_obj2.last_modified = datetime(2023, 1, 2)
        
        with patch('api.services.minio_services.object_service.minio_client') as mock_client:
            mock_client.client.bucket_exists.return_value = True
            mock_client.client.list_objects.return_value = [mock_obj1, mock_obj2]
            
            result = await object_service.list_objects("test-bucket")
            
            assert len(result.objects) == 2
            assert result.objects[0].key == "obj1"
            assert result.objects[1].key == "obj2"
    
    @pytest.mark.asyncio
    async def test_get_object_metadata_success(self):
        """Test successful object metadata retrieval."""
        mock_stat = Mock()
        mock_stat.size = 100
        mock_stat.content_type = "text/plain"
        mock_stat.last_modified = datetime(2023, 1, 1)
        mock_stat.etag = "test-etag"
        mock_stat.metadata = {"custom": "value"}
        
        with patch('api.services.minio_services.object_service.minio_client') as mock_client:
            mock_client.client.stat_object.return_value = mock_stat
            
            result = await object_service.get_object_metadata("test-bucket", "test-key")
            
            assert result.key == "test-key"
            assert result.size == 100
            assert result.content_type == "text/plain"
            assert result.metadata == {"custom": "value"}
    
    @pytest.mark.asyncio
    async def test_delete_object_success(self):
        """Test successful object deletion."""
        mock_stat = Mock()
        
        with patch('api.services.minio_services.object_service.minio_client') as mock_client:
            mock_client.client.stat_object.return_value = mock_stat
            mock_client.client.remove_object.return_value = None
            
            result = await object_service.delete_object("test-bucket", "test-key")
            
            assert result is True
            mock_client.client.remove_object.assert_called_once_with("test-bucket", "test-key")
    
    @pytest.mark.asyncio
    async def test_delete_object_not_found(self):
        """Test object deletion when object doesn't exist."""
        with patch('api.services.minio_services.object_service.minio_client') as mock_client:
            mock_client.client.stat_object.side_effect = create_s3_error_mock("No such key", "NoSuchKey")
            
            with pytest.raises(S3Error, match="Object 'test-key' does not exist"):
                await object_service.delete_object("test-bucket", "test-key")
    
    @pytest.mark.asyncio
    async def test_generate_presigned_upload_url_success(self):
        """Test successful presigned upload URL generation."""
        with patch('api.services.minio_services.object_service.minio_client') as mock_client:
            mock_client.client.bucket_exists.return_value = True
            mock_client.client.presigned_put_object.return_value = "https://presigned-url"
            
            result = await object_service.generate_presigned_upload_url(
                "test-bucket", "test-key", 3600
            )
            
            assert result.url == "https://presigned-url"
            assert result.expires_in == 3600
    
    @pytest.mark.asyncio
    async def test_generate_presigned_download_url_success(self):
        """Test successful presigned download URL generation."""
        mock_stat = Mock()
        
        with patch('api.services.minio_services.object_service.minio_client') as mock_client:
            mock_client.client.stat_object.return_value = mock_stat
            mock_client.client.presigned_get_object.return_value = "https://presigned-download-url"
            
            result = await object_service.generate_presigned_download_url(
                "test-bucket", "test-key", 1800
            )
            
            assert result.url == "https://presigned-download-url"
            assert result.expires_in == 1800