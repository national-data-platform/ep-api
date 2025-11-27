import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, Mock, AsyncMock
from minio.error import S3Error
import io
from datetime import datetime

from api.main import app
from api.models.minio_models import BucketListResponse, BucketInfo, ObjectListResponse, ObjectInfo
from api.services.auth_services.get_current_user import get_current_user

# Mock authentication for all tests
def mock_get_current_user():
    return {"user": "test_user", "groups": ["test_group"]}

# Mock S3Error class that inherits from S3Error 
class MockS3Error(S3Error):
    def __init__(self, message, code):
        # Create a minimal mock response
        mock_response = Mock()
        mock_response.status = 409
        mock_response.data = b""
        mock_response.headers = {}
        
        # Call parent constructor with required parameters  
        super().__init__(code, message, "resource", "request_id", "host_id", mock_response)

# Helper function to create S3Error mocks
def create_s3_error_mock(message, code):
    return MockS3Error(message, code)

# Apply the mock to all auth dependencies
app.dependency_overrides[get_current_user] = mock_get_current_user

client = TestClient(app)


class TestBucketRoutes:
    """Test S3 bucket API endpoints."""
    
    def setup_method(self):
        """Setup for each test method."""
        self.headers = {"Authorization": "Bearer test_token"}
    
    @patch('api.routes.minio_routes.bucket_routes.s3_settings')
    def test_create_bucket_service_not_configured(self, mock_settings):
        """Test bucket creation when S3 is not configured."""
        mock_settings.is_configured = False
        
        response = client.post(
            "/s3/buckets/",
            json={"name": "test-bucket"},
            headers=self.headers
        )
        
        assert response.status_code == 503
        assert "S3 service is not configured" in response.json()["detail"]
    
    @patch('api.routes.minio_routes.bucket_routes.bucket_service.create_bucket')
    @patch('api.routes.minio_routes.bucket_routes.s3_settings')
    def test_create_bucket_success(self, mock_settings, mock_create):
        """Test successful bucket creation."""
        mock_settings.is_configured = True
        mock_create.return_value = True
        
        response = client.post(
            "/s3/buckets/",
            json={"name": "test-bucket"},
            headers=self.headers
        )
        
        assert response.status_code == 201
        data = response.json()
        assert "Bucket 'test-bucket' created successfully" in data["message"]
        assert data["success"] is True
    
    @patch('api.routes.minio_routes.bucket_routes.bucket_service.create_bucket')
    @patch('api.routes.minio_routes.bucket_routes.s3_settings')
    def test_create_bucket_already_exists(self, mock_settings, mock_create):
        """Test bucket creation when bucket already exists."""
        mock_settings.is_configured = True
        mock_create.side_effect = create_s3_error_mock("Bucket already exists", "BucketAlreadyExists")
        
        response = client.post(
            "/s3/buckets/",
            json={"name": "test-bucket"},
            headers=self.headers
        )
        
        assert response.status_code == 409
        assert "Bucket 'test-bucket' already exists" in response.json()["detail"]
    
    @patch('api.routes.minio_routes.bucket_routes.bucket_service.list_buckets')
    @patch('api.routes.minio_routes.bucket_routes.s3_settings')
    def test_list_buckets_success(self, mock_settings, mock_list):
        """Test successful bucket listing."""
        mock_settings.is_configured = True
        
        bucket1 = BucketInfo(name="bucket1", creation_date=datetime(2023, 1, 1))
        bucket2 = BucketInfo(name="bucket2", creation_date=datetime(2023, 1, 2))
        mock_list.return_value = BucketListResponse(buckets=[bucket1, bucket2])
        
        response = client.get("/s3/buckets/", headers=self.headers)
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["buckets"]) == 2
        assert data["buckets"][0]["name"] == "bucket1"
        assert data["buckets"][1]["name"] == "bucket2"
    
    @patch('api.routes.minio_routes.bucket_routes.bucket_service.get_bucket_info')
    @patch('api.routes.minio_routes.bucket_routes.s3_settings')
    def test_get_bucket_info_success(self, mock_settings, mock_get):
        """Test successful bucket info retrieval."""
        mock_settings.is_configured = True
        mock_get.return_value = BucketInfo(name="test-bucket", creation_date=datetime(2023, 1, 1))
        
        response = client.get("/s3/buckets/test-bucket", headers=self.headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "test-bucket"
    
    @patch('api.routes.minio_routes.bucket_routes.bucket_service.get_bucket_info')
    @patch('api.routes.minio_routes.bucket_routes.s3_settings')
    def test_get_bucket_info_not_found(self, mock_settings, mock_get):
        """Test bucket info retrieval for non-existent bucket."""
        mock_settings.is_configured = True
        mock_get.side_effect = create_s3_error_mock("No such bucket", "NoSuchBucket")
        
        response = client.get("/s3/buckets/nonexistent", headers=self.headers)
        
        assert response.status_code == 404
        assert "Bucket 'nonexistent' not found" in response.json()["detail"]
    
    @patch('api.routes.minio_routes.bucket_routes.bucket_service.delete_bucket')
    @patch('api.routes.minio_routes.bucket_routes.s3_settings')
    def test_delete_bucket_success(self, mock_settings, mock_delete):
        """Test successful bucket deletion."""
        mock_settings.is_configured = True
        mock_delete.return_value = True
        
        response = client.delete("/s3/buckets/test-bucket", headers=self.headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "Bucket 'test-bucket' deleted successfully" in data["message"]
        assert data["success"] is True
    
    @patch('api.routes.minio_routes.bucket_routes.bucket_service.delete_bucket')
    @patch('api.routes.minio_routes.bucket_routes.s3_settings')
    def test_delete_bucket_not_empty(self, mock_settings, mock_delete):
        """Test bucket deletion when bucket is not empty."""
        mock_settings.is_configured = True
        mock_delete.side_effect = create_s3_error_mock("Bucket not empty", "BucketNotEmpty")
        
        response = client.delete("/s3/buckets/test-bucket", headers=self.headers)
        
        assert response.status_code == 409
        assert "Bucket 'test-bucket' is not empty" in response.json()["detail"]


class TestObjectRoutes:
    """Test S3 object API endpoints."""
    
    def setup_method(self):
        """Setup for each test method."""
        self.headers = {"Authorization": "Bearer test_token"}
    
    @patch('api.routes.minio_routes.object_routes.s3_settings')
    def test_upload_object_service_not_configured(self, mock_settings):
        """Test object upload when S3 is not configured."""
        mock_settings.is_configured = False
        
        files = {"file": ("test.txt", io.BytesIO(b"test content"), "text/plain")}
        response = client.post(
            "/s3/objects/test-bucket",
            files=files,
            headers=self.headers
        )
        
        assert response.status_code == 503
        assert "S3 service is not configured" in response.json()["detail"]
    
    @patch('api.routes.minio_routes.object_routes.object_service.upload_object')
    @patch('api.routes.minio_routes.object_routes.s3_settings')
    def test_upload_object_success(self, mock_settings, mock_upload):
        """Test successful object upload."""
        mock_settings.is_configured = True
        mock_upload.return_value = Mock(
            bucket="test-bucket",
            key="test.txt",
            size=12,
            etag="test-etag"
        )
        
        files = {"file": ("test.txt", io.BytesIO(b"test content"), "text/plain")}
        response = client.post(
            "/s3/objects/test-bucket",
            files=files,
            headers=self.headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["bucket"] == "test-bucket"
        assert data["key"] == "test.txt"
        assert data["size"] == 12
    
    @patch('api.routes.minio_routes.object_routes.object_service.upload_object')
    @patch('api.routes.minio_routes.object_routes.s3_settings')
    def test_upload_object_bucket_not_found(self, mock_settings, mock_upload):
        """Test object upload to non-existent bucket."""
        mock_settings.is_configured = True
        mock_upload.side_effect = create_s3_error_mock("No such bucket", "NoSuchBucket")
        
        files = {"file": ("test.txt", io.BytesIO(b"test content"), "text/plain")}
        response = client.post(
            "/s3/objects/nonexistent",
            files=files,
            headers=self.headers
        )
        
        assert response.status_code == 404
        assert "Bucket 'nonexistent' not found" in response.json()["detail"]
    
    @patch('api.routes.minio_routes.object_routes.object_service.list_objects')
    @patch('api.routes.minio_routes.object_routes.s3_settings')
    def test_list_objects_success(self, mock_settings, mock_list):
        """Test successful object listing."""
        mock_settings.is_configured = True
        
        obj1 = ObjectInfo(
            key="obj1.txt",
            size=100,
            etag="etag1",
            last_modified=datetime(2023, 1, 1),
            content_type="text/plain"
        )
        obj2 = ObjectInfo(
            key="obj2.txt",
            size=200,
            etag="etag2",
            last_modified=datetime(2023, 1, 2),
            content_type="text/plain"
        )
        mock_list.return_value = ObjectListResponse(objects=[obj1, obj2])
        
        response = client.get("/s3/objects/test-bucket", headers=self.headers)
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["objects"]) == 2
        assert data["objects"][0]["key"] == "obj1.txt"
        assert data["objects"][1]["key"] == "obj2.txt"
    
    @patch('api.routes.minio_routes.object_routes.object_service.get_object_metadata')
    @patch('api.routes.minio_routes.object_routes.minio_client')
    @patch('api.routes.minio_routes.object_routes.s3_settings')
    def test_download_object_success(self, mock_settings, mock_minio_client, mock_metadata):
        """Test successful object download."""
        mock_settings.is_configured = True
        
        # Mock metadata
        mock_metadata.return_value = Mock(
            content_type="text/plain",
            size=12
        )
        
        # Mock MINIO client response
        mock_response = Mock()
        mock_response.read.return_value = b"test content"
        mock_response.close = Mock()
        mock_response.release_conn = Mock()
        mock_minio_client.client.get_object.return_value = mock_response
        
        response = client.get("/s3/objects/test-bucket/test.txt", headers=self.headers)
        
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/plain")
    
    @patch('api.routes.minio_routes.object_routes.object_service.delete_object')
    @patch('api.routes.minio_routes.object_routes.s3_settings')
    def test_delete_object_success(self, mock_settings, mock_delete):
        """Test successful object deletion."""
        mock_settings.is_configured = True
        mock_delete.return_value = True
        
        response = client.delete(
            "/s3/objects/test-bucket/test.txt",
            headers=self.headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "Object 'test.txt' deleted successfully" in data["message"]
        assert data["success"] is True
    
    @patch('api.routes.minio_routes.object_routes.object_service.delete_object')
    @patch('api.routes.minio_routes.object_routes.s3_settings')
    def test_delete_object_not_found(self, mock_settings, mock_delete):
        """Test object deletion when object doesn't exist."""
        mock_settings.is_configured = True
        mock_delete.side_effect = create_s3_error_mock("No such key", "NoSuchKey")
        
        response = client.delete(
            "/s3/objects/test-bucket/nonexistent.txt",
            headers=self.headers
        )
        
        assert response.status_code == 404
        assert "Object 'nonexistent.txt' not found" in response.json()["detail"]
    
    @patch('api.routes.minio_routes.object_routes.object_service.get_object_metadata')
    @patch('api.routes.minio_routes.object_routes.s3_settings')
    def test_get_object_metadata_success(self, mock_settings, mock_metadata):
        """Test successful object metadata retrieval."""
        mock_settings.is_configured = True
        mock_metadata.return_value = Mock(
            key="test.txt",
            size=100,
            content_type="text/plain",
            last_modified=datetime(2023, 1, 1),
            etag="test-etag",
            metadata={"custom": "value"}
        )
        
        response = client.get(
            "/s3/objects/test-bucket/test.txt/metadata",
            headers=self.headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["key"] == "test.txt"
        assert data["size"] == 100
        assert data["content_type"] == "text/plain"
    
    @patch('api.routes.minio_routes.object_routes.object_service.generate_presigned_upload_url')
    @patch('api.routes.minio_routes.object_routes.s3_settings')
    def test_generate_presigned_upload_url_success(self, mock_settings, mock_presigned):
        """Test successful presigned upload URL generation."""
        mock_settings.is_configured = True
        mock_presigned.return_value = Mock(
            url="https://presigned-upload-url",
            expires_in=3600
        )
        
        response = client.post(
            "/s3/objects/test-bucket/test.txt/presigned-upload",
            json={"expires_in": 3600},
            headers=self.headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["url"] == "https://presigned-upload-url"
        assert data["expires_in"] == 3600
    
    @patch('api.routes.minio_routes.object_routes.object_service.generate_presigned_download_url')
    @patch('api.routes.minio_routes.object_routes.s3_settings')
    def test_generate_presigned_download_url_success(self, mock_settings, mock_presigned):
        """Test successful presigned download URL generation."""
        mock_settings.is_configured = True
        mock_presigned.return_value = Mock(
            url="https://presigned-download-url",
            expires_in=1800
        )
        
        response = client.post(
            "/s3/objects/test-bucket/test.txt/presigned-download",
            json={"expires_in": 1800},
            headers=self.headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["url"] == "https://presigned-download-url"
        assert data["expires_in"] == 1800


class TestMinioModels:
    """Test MINIO Pydantic models."""
    
    def test_bucket_create_request_valid(self):
        """Test valid bucket create request."""
        from api.models.minio_models import BucketCreateRequest
        
        request = BucketCreateRequest(name="test-bucket", region="us-east-1")
        assert request.name == "test-bucket"
        assert request.region == "us-east-1"
    
    def test_bucket_create_request_minimal(self):
        """Test minimal bucket create request."""
        from api.models.minio_models import BucketCreateRequest
        
        request = BucketCreateRequest(name="test-bucket")
        assert request.name == "test-bucket"
        assert request.region is None
    
    def test_presigned_url_request_default_expires(self):
        """Test presigned URL request with default expiration."""
        from api.models.minio_models import PresignedUrlRequest
        
        request = PresignedUrlRequest()
        assert request.expires_in == 3600
    
    def test_presigned_url_request_custom_expires(self):
        """Test presigned URL request with custom expiration."""
        from api.models.minio_models import PresignedUrlRequest
        
        request = PresignedUrlRequest(expires_in=7200)
        assert request.expires_in == 7200