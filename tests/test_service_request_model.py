# tests/test_service_request_model.py
"""
Tests for ServiceRequest model.

Tests for api/models/service_request_model.py
"""

import pytest
from pydantic import ValidationError
from api.models.service_request_model import ServiceRequest


class TestServiceRequestCreation:
    """Tests for ServiceRequest model creation."""

    def test_create_with_required_fields(self):
        """Test creating ServiceRequest with only required fields."""
        service = ServiceRequest(
            service_name="test_service",
            service_title="Test Service",
            owner_org="services",
            service_url="https://api.example.com/test"
        )

        assert service.service_name == "test_service"
        assert service.service_title == "Test Service"
        assert service.owner_org == "services"
        assert service.service_url == "https://api.example.com/test"
        assert service.service_type is None
        assert service.notes is None
        assert service.extras is None
        assert service.health_check_url is None
        assert service.documentation_url is None

    def test_create_with_all_fields(self):
        """Test creating ServiceRequest with all fields."""
        service = ServiceRequest(
            service_name="auth_api",
            service_title="Authentication API",
            owner_org="services",
            service_url="https://api.example.com/auth",
            service_type="API",
            notes="User authentication service",
            extras={"version": "1.0.0", "env": "prod"},
            health_check_url="https://api.example.com/auth/health",
            documentation_url="https://docs.example.com/auth"
        )

        assert service.service_name == "auth_api"
        assert service.service_type == "API"
        assert service.notes == "User authentication service"
        assert service.extras == {"version": "1.0.0", "env": "prod"}
        assert service.health_check_url == "https://api.example.com/auth/health"
        assert service.documentation_url == "https://docs.example.com/auth"

    def test_create_with_http_url(self):
        """Test creating ServiceRequest with http:// URL."""
        service = ServiceRequest(
            service_name="test",
            service_title="Test",
            owner_org="services",
            service_url="http://localhost:8000/api"
        )

        assert service.service_url == "http://localhost:8000/api"

    def test_create_with_optional_urls(self):
        """Test creating with optional health check and documentation URLs."""
        service = ServiceRequest(
            service_name="test",
            service_title="Test",
            owner_org="services",
            service_url="https://api.example.com",
            health_check_url="https://api.example.com/health",
            documentation_url="http://docs.example.com"
        )

        assert service.health_check_url == "https://api.example.com/health"
        assert service.documentation_url == "http://docs.example.com"


class TestServiceRequestValidation:
    """Tests for ServiceRequest validation."""

    def test_missing_required_field_raises_error(self):
        """Test that missing required fields raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ServiceRequest(
                service_name="test",
                service_title="Test"
                # Missing owner_org and service_url
            )

        errors = exc_info.value.errors()
        field_names = [e["loc"][0] for e in errors]
        assert "owner_org" in field_names
        assert "service_url" in field_names

    def test_empty_service_name_raises_error(self):
        """Test that empty service_name raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ServiceRequest(
                service_name="",
                service_title="Test",
                owner_org="services",
                service_url="https://api.example.com"
            )

        errors = exc_info.value.errors()
        assert any(e["loc"][0] == "service_name" for e in errors)

    def test_empty_service_title_raises_error(self):
        """Test that empty service_title raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ServiceRequest(
                service_name="test",
                service_title="",
                owner_org="services",
                service_url="https://api.example.com"
            )

        errors = exc_info.value.errors()
        assert any(e["loc"][0] == "service_title" for e in errors)

    def test_service_name_too_long_raises_error(self):
        """Test that service_name > 100 chars raises ValidationError."""
        long_name = "a" * 101

        with pytest.raises(ValidationError) as exc_info:
            ServiceRequest(
                service_name=long_name,
                service_title="Test",
                owner_org="services",
                service_url="https://api.example.com"
            )

        errors = exc_info.value.errors()
        assert any(e["loc"][0] == "service_name" for e in errors)

    def test_service_title_too_long_raises_error(self):
        """Test that service_title > 200 chars raises ValidationError."""
        long_title = "a" * 201

        with pytest.raises(ValidationError) as exc_info:
            ServiceRequest(
                service_name="test",
                service_title=long_title,
                owner_org="services",
                service_url="https://api.example.com"
            )

        errors = exc_info.value.errors()
        assert any(e["loc"][0] == "service_title" for e in errors)

    def test_service_type_too_long_raises_error(self):
        """Test that service_type > 50 chars raises ValidationError."""
        long_type = "a" * 51

        with pytest.raises(ValidationError) as exc_info:
            ServiceRequest(
                service_name="test",
                service_title="Test",
                owner_org="services",
                service_url="https://api.example.com",
                service_type=long_type
            )

        errors = exc_info.value.errors()
        assert any(e["loc"][0] == "service_type" for e in errors)


class TestOwnerOrgValidation:
    """Tests for owner_org validation."""

    def test_owner_org_must_be_services(self):
        """Test that owner_org must be 'services'."""
        service = ServiceRequest(
            service_name="test",
            service_title="Test",
            owner_org="services",
            service_url="https://api.example.com"
        )

        assert service.owner_org == "services"

    def test_invalid_owner_org_raises_error(self):
        """Test that owner_org != 'services' raises ValueError."""
        with pytest.raises(ValidationError) as exc_info:
            ServiceRequest(
                service_name="test",
                service_title="Test",
                owner_org="other_org",
                service_url="https://api.example.com"
            )

        errors = exc_info.value.errors()
        assert any(e["loc"][0] == "owner_org" for e in errors)
        assert any("services" in str(e["msg"]).lower() for e in errors)

    def test_empty_owner_org_raises_error(self):
        """Test that empty owner_org raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ServiceRequest(
                service_name="test",
                service_title="Test",
                owner_org="",
                service_url="https://api.example.com"
            )

        errors = exc_info.value.errors()
        assert any(e["loc"][0] == "owner_org" for e in errors)


class TestURLValidation:
    """Tests for URL validation."""

    def test_service_url_must_start_with_http(self):
        """Test that service_url must start with http:// or https://."""
        with pytest.raises(ValidationError) as exc_info:
            ServiceRequest(
                service_name="test",
                service_title="Test",
                owner_org="services",
                service_url="ftp://example.com"
            )

        errors = exc_info.value.errors()
        assert any(e["loc"][0] == "service_url" for e in errors)
        assert any("http" in str(e["msg"]).lower() for e in errors)

    def test_service_url_without_protocol_raises_error(self):
        """Test that service_url without protocol raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ServiceRequest(
                service_name="test",
                service_title="Test",
                owner_org="services",
                service_url="api.example.com"
            )

        errors = exc_info.value.errors()
        assert any(e["loc"][0] == "service_url" for e in errors)

    def test_health_check_url_must_start_with_http(self):
        """Test that health_check_url must start with http:// or https://."""
        with pytest.raises(ValidationError) as exc_info:
            ServiceRequest(
                service_name="test",
                service_title="Test",
                owner_org="services",
                service_url="https://api.example.com",
                health_check_url="ftp://example.com/health"
            )

        errors = exc_info.value.errors()
        assert any(e["loc"][0] == "health_check_url" for e in errors)

    def test_documentation_url_must_start_with_http(self):
        """Test that documentation_url must start with http:// or https://."""
        with pytest.raises(ValidationError) as exc_info:
            ServiceRequest(
                service_name="test",
                service_title="Test",
                owner_org="services",
                service_url="https://api.example.com",
                documentation_url="file:///docs"
            )

        errors = exc_info.value.errors()
        assert any(e["loc"][0] == "documentation_url" for e in errors)

    def test_none_urls_are_valid(self):
        """Test that None is valid for optional URL fields."""
        service = ServiceRequest(
            service_name="test",
            service_title="Test",
            owner_org="services",
            service_url="https://api.example.com",
            health_check_url=None,
            documentation_url=None
        )

        assert service.health_check_url is None
        assert service.documentation_url is None


class TestServiceRequestExtras:
    """Tests for extras field."""

    def test_extras_with_various_types(self):
        """Test that extras can contain various data types."""
        service = ServiceRequest(
            service_name="test",
            service_title="Test",
            owner_org="services",
            service_url="https://api.example.com",
            extras={
                "version": "1.0.0",
                "port": 8080,
                "enabled": True,
                "tags": ["api", "auth"],
                "config": {"timeout": 30}
            }
        )

        assert service.extras["version"] == "1.0.0"
        assert service.extras["port"] == 8080
        assert service.extras["enabled"] is True
        assert service.extras["tags"] == ["api", "auth"]
        assert service.extras["config"] == {"timeout": 30}

    def test_empty_extras_dict(self):
        """Test that empty extras dict is valid."""
        service = ServiceRequest(
            service_name="test",
            service_title="Test",
            owner_org="services",
            service_url="https://api.example.com",
            extras={}
        )

        assert service.extras == {}


class TestServiceRequestModelDict:
    """Tests for model dict conversion."""

    def test_model_dict_includes_all_fields(self):
        """Test that model_dump includes all fields."""
        service = ServiceRequest(
            service_name="test",
            service_title="Test Service",
            owner_org="services",
            service_url="https://api.example.com",
            service_type="API"
        )

        data = service.model_dump()
        assert "service_name" in data
        assert "service_title" in data
        assert "owner_org" in data
        assert "service_url" in data
        assert "service_type" in data

    def test_model_dict_excludes_none_values(self):
        """Test that model_dump can exclude None values."""
        service = ServiceRequest(
            service_name="test",
            service_title="Test",
            owner_org="services",
            service_url="https://api.example.com"
        )

        data = service.model_dump(exclude_none=True)
        assert "service_name" in data
        assert "notes" not in data
        assert "extras" not in data
        assert "health_check_url" not in data
