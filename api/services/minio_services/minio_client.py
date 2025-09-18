from minio import Minio
from minio.error import S3Error
from api.config.minio_settings import s3_settings
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class MinioClient:
    """MINIO client wrapper."""
    
    def __init__(self):
        self._client: Optional[Minio] = None
    
    @property
    def client(self) -> Minio:
        """Get MINIO client instance."""
        if not s3_settings.is_configured:
            raise ValueError("S3 is not properly configured")
        
        if self._client is None:
            try:
                self._client = Minio(
                    endpoint=s3_settings.endpoint,
                    access_key=s3_settings.access_key,
                    secret_key=s3_settings.secret_key,
                    secure=s3_settings.secure,
                    region=s3_settings.region
                )
                logger.info(f"S3 client initialized for endpoint: {s3_settings.endpoint}")
            except Exception as e:
                logger.error(f"Failed to initialize S3 client: {str(e)}")
                raise
        
        return self._client
    
    def test_connection(self) -> bool:
        """Test S3 connection."""
        try:
            list(self.client.list_buckets())
            return True
        except S3Error as e:
            logger.error(f"S3 connection test failed: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error testing S3 connection: {str(e)}")
            return False


minio_client = MinioClient()