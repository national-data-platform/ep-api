import pytest
from unittest.mock import patch
import os

from api.config.minio_settings import S3Settings, s3_settings


class TestS3Settings:
    """Test S3 configuration settings."""
    
    def test_s3_settings_default_values(self):
        """Test S3 settings with default values."""
        with patch.dict(os.environ, {}, clear=True):
            settings = S3Settings(_env_file=None)
            
            assert settings.enabled is False
            assert settings.endpoint == "localhost:9000"
            assert settings.access_key == "minioadmin"
            assert settings.secret_key == "minioadmin123"
            assert settings.secure is False
            assert settings.region == "us-east-1"
    
    def test_s3_settings_from_environment(self):
        """Test S3 settings from environment variables."""
        env_vars = {
            "S3_ENABLED": "True",
            "S3_ENDPOINT": "s3.example.com:9000",
            "S3_ACCESS_KEY": "test_access",
            "S3_SECRET_KEY": "test_secret",
            "S3_SECURE": "True",
            "S3_REGION": "eu-west-1"
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            settings = S3Settings(_env_file=None)
            
            assert settings.enabled is True
            assert settings.endpoint == "s3.example.com:9000"
            assert settings.access_key == "test_access"
            assert settings.secret_key == "test_secret"
            assert settings.secure is True
            assert settings.region == "eu-west-1"
    
    def test_s3_settings_boolean_parsing(self):
        """Test boolean parsing for S3 settings."""
        # Test true values
        with patch.dict(os.environ, {"S3_ENABLED": "true"}, clear=True):
            settings = S3Settings(_env_file=None)
            assert settings.enabled is True
            
        # Test false values
        false_values = ["False", "false", "FALSE", "0", "no"]
        for value in false_values:
            with patch.dict(os.environ, {"S3_ENABLED": value}, clear=True):
                settings = S3Settings(_env_file=None)
                assert settings.enabled is False
    
    def test_is_configured_true(self):
        """Test is_configured returns True when properly configured."""
        env_vars = {
            "S3_ENABLED": "True",
            "S3_ENDPOINT": "localhost:9000",
            "S3_ACCESS_KEY": "access",
            "S3_SECRET_KEY": "secret"
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            settings = S3Settings(_env_file=None)
            assert settings.is_configured is True
    
    def test_is_configured_false_disabled(self):
        """Test is_configured returns False when disabled."""
        env_vars = {
            "S3_ENABLED": "False",
            "S3_ENDPOINT": "localhost:9000",
            "S3_ACCESS_KEY": "access",
            "S3_SECRET_KEY": "secret"
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            settings = S3Settings(_env_file=None)
            assert settings.is_configured is False
    
    def test_is_configured_false_missing_endpoint(self):
        """Test is_configured returns False when endpoint is missing."""
        env_vars = {
            "S3_ENABLED": "True",
            "S3_ENDPOINT": "",
            "S3_ACCESS_KEY": "access",
            "S3_SECRET_KEY": "secret"
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            settings = S3Settings(_env_file=None)
            assert settings.is_configured is False
    
    def test_is_configured_false_missing_credentials(self):
        """Test is_configured returns False when credentials are missing."""
        env_vars = {
            "S3_ENABLED": "True",
            "S3_ENDPOINT": "localhost:9000",
            "S3_ACCESS_KEY": "",
            "S3_SECRET_KEY": ""
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            settings = S3Settings(_env_file=None)
            assert settings.is_configured is False
    
    def test_global_s3_settings_instance(self):
        """Test that the global s3_settings instance exists."""
        assert s3_settings is not None
        assert isinstance(s3_settings, S3Settings)