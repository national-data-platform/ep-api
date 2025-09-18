import pytest
from unittest.mock import Mock, patch
from fastapi import HTTPException

from api.services.auth_services.authorization_service import check_organization_membership


class TestAuthServices:
    """Test authentication and authorization services."""
    
    def test_check_organization_membership_enabled_matching_org(self):
        """Test organization membership check when enabled and org matches."""
        user_info = {"groups": ["Test Org"]}
        
        with patch('api.services.auth_services.authorization_service.swagger_settings') as mock_settings:
            mock_settings.enable_organization_based_access = True
            mock_settings.organization = "Test Org"
            
            result = check_organization_membership(user_info)
            assert result is True
    
    def test_check_organization_membership_enabled_different_org(self):
        """Test organization membership check when enabled and org doesn't match."""
        user_info = {"groups": ["Different Org"]}
        
        with patch('api.services.auth_services.authorization_service.swagger_settings') as mock_settings:
            mock_settings.enable_organization_based_access = True
            mock_settings.organization = "Test Org"
            
            result = check_organization_membership(user_info)
            assert result is False
    
    def test_check_organization_membership_disabled(self):
        """Test organization membership check when disabled."""
        user_info = {"groups": ["Any Org"]}
        
        with patch('api.services.auth_services.authorization_service.swagger_settings') as mock_settings:
            mock_settings.enable_organization_based_access = False
            
            result = check_organization_membership(user_info)
            assert result is True
    
    def test_organization_membership_empty_groups(self):
        """Test organization membership with empty groups."""
        user_info = {"groups": []}
        
        with patch('api.services.auth_services.authorization_service.swagger_settings') as mock_settings:
            mock_settings.enable_organization_based_access = True
            mock_settings.organization = "Test Org"
            
            result = check_organization_membership(user_info)
            assert result is False
    
    def test_organization_membership_case_insensitive(self):
        """Test organization membership is case insensitive."""
        user_info = {"groups": ["test org"]}
        
        with patch('api.services.auth_services.authorization_service.swagger_settings') as mock_settings:
            mock_settings.enable_organization_based_access = True
            mock_settings.organization = "Test Org"
            
            result = check_organization_membership(user_info)
            assert result is True




class TestConfigValidation:
    """Test configuration validation."""
    
    def test_ckan_settings_validation(self):
        """Test CKAN settings validation."""
        from api.config.ckan_settings import ckan_settings
        
        # Test that settings object exists and has expected attributes
        assert hasattr(ckan_settings, 'ckan_local_enabled')
        assert hasattr(ckan_settings, 'ckan_url')
        assert hasattr(ckan_settings, 'ckan_api_key')
        assert hasattr(ckan_settings, 'pre_ckan_enabled')
    
    def test_kafka_settings_validation(self):
        """Test Kafka settings validation."""
        from api.config.kafka_settings import kafka_settings
        
        # Test that settings object exists and has expected attributes
        assert hasattr(kafka_settings, 'kafka_connection')
        assert hasattr(kafka_settings, 'kafka_host')
        assert hasattr(kafka_settings, 'kafka_port')
    
    def test_main_app_creation(self):
        """Test that FastAPI app is created correctly."""
        from api.main import app
        
        assert app is not None
        assert app.title is not None
        assert app.version is not None


class TestModelValidation:
    """Test model validation edge cases."""
    
    def test_token_model_validation(self):
        """Test token model validation."""
        from api.models.token_model import Token
        
        # Test valid token
        token = Token(access_token="test_token", token_type="bearer")
        assert token.access_token == "test_token"
        assert token.token_type == "bearer"