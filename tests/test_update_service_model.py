# tests/test_update_service_model.py
"""
Tests for ServiceUpdateRequest model validation.
"""

import pytest
from pydantic import ValidationError

from api.models.update_service_model import ServiceUpdateRequest


class TestServiceUpdateRequestValidation:
    """Test validation for ServiceUpdateRequest model."""

    def test_all_fields_optional(self):
        """Test that all fields are optional."""
        request = ServiceUpdateRequest()

        assert request.service_name is None
        assert request.service_title is None
        assert request.owner_org is None
        assert request.service_url is None

    def test_valid_complete_request(self):
        """Test valid complete request with all fields."""
        request = ServiceUpdateRequest(
            service_name="test_service",
            service_title="Test Service",
            owner_org="services",
            service_url="https://example.com/api",
            service_type="REST API",
            notes="Test notes",
            extras={"version": "1.0"},
            health_check_url="https://example.com/health",
            documentation_url="https://example.com/docs",
        )

        assert request.service_name == "test_service"
        assert request.service_title == "Test Service"
        assert request.owner_org == "services"
        assert request.service_url == "https://example.com/api"

    def test_partial_update_with_few_fields(self):
        """Test partial update with only some fields."""
        request = ServiceUpdateRequest(
            service_title="Updated Title", notes="Updated notes"
        )

        assert request.service_title == "Updated Title"
        assert request.notes == "Updated notes"
        assert request.service_name is None


class TestOwnerOrgValidation:
    """Test owner_org field validation."""

    def test_owner_org_must_be_services(self):
        """Test that owner_org must be 'services'."""
        request = ServiceUpdateRequest(owner_org="services")

        assert request.owner_org == "services"

    def test_owner_org_invalid_value_raises_error(self):
        """Test that invalid owner_org raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ServiceUpdateRequest(owner_org="invalid-org")

        assert "pattern" in str(exc_info.value).lower() or "services" in str(
            exc_info.value
        )

    def test_owner_org_can_be_none(self):
        """Test that owner_org can be None."""
        request = ServiceUpdateRequest(owner_org=None)

        assert request.owner_org is None


class TestURLValidation:
    """Test URL field validation."""

    def test_service_url_valid_http(self):
        """Test that http URLs are valid."""
        request = ServiceUpdateRequest(service_url="http://example.com/api")

        assert request.service_url == "http://example.com/api"

    def test_service_url_valid_https(self):
        """Test that https URLs are valid."""
        request = ServiceUpdateRequest(service_url="https://example.com/api")

        assert request.service_url == "https://example.com/api"

    def test_service_url_invalid_no_protocol(self):
        """Test that URLs without protocol raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ServiceUpdateRequest(service_url="example.com/api")

        assert "must start with http:// or https://" in str(exc_info.value)

    def test_health_check_url_valid(self):
        """Test that health_check_url accepts valid URLs."""
        request = ServiceUpdateRequest(health_check_url="https://example.com/health")

        assert request.health_check_url == "https://example.com/health"

    def test_health_check_url_invalid(self):
        """Test that invalid health_check_url raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ServiceUpdateRequest(health_check_url="ftp://example.com/health")

        assert "must start with http:// or https://" in str(exc_info.value)

    def test_documentation_url_valid(self):
        """Test that documentation_url accepts valid URLs."""
        request = ServiceUpdateRequest(documentation_url="https://docs.example.com")

        assert request.documentation_url == "https://docs.example.com"

    def test_documentation_url_invalid(self):
        """Test that invalid documentation_url raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ServiceUpdateRequest(documentation_url="invalid-url")

        assert "must start with http:// or https://" in str(exc_info.value)

    def test_all_urls_can_be_none(self):
        """Test that all URL fields can be None."""
        request = ServiceUpdateRequest(
            service_url=None, health_check_url=None, documentation_url=None
        )

        assert request.service_url is None
        assert request.health_check_url is None
        assert request.documentation_url is None


class TestFieldConstraints:
    """Test field length and pattern constraints."""

    def test_service_name_min_length(self):
        """Test that service_name has minimum length constraint."""
        with pytest.raises(ValidationError) as exc_info:
            ServiceUpdateRequest(service_name="")

        assert "at least 1 character" in str(exc_info.value)

    def test_service_name_max_length(self):
        """Test that service_name has maximum length constraint."""
        with pytest.raises(ValidationError) as exc_info:
            ServiceUpdateRequest(service_name="x" * 101)

        assert "at most 100 character" in str(exc_info.value)

    def test_service_title_min_length(self):
        """Test that service_title has minimum length constraint."""
        with pytest.raises(ValidationError) as exc_info:
            ServiceUpdateRequest(service_title="")

        assert "at least 1 character" in str(exc_info.value)

    def test_service_title_max_length(self):
        """Test that service_title has maximum length constraint."""
        with pytest.raises(ValidationError) as exc_info:
            ServiceUpdateRequest(service_title="x" * 201)

        assert "at most 200 character" in str(exc_info.value)

    def test_service_type_max_length(self):
        """Test that service_type has maximum length constraint."""
        with pytest.raises(ValidationError) as exc_info:
            ServiceUpdateRequest(service_type="x" * 51)

        assert "at most 50 character" in str(exc_info.value)


class TestExtrasField:
    """Test extras field for additional metadata."""

    def test_extras_with_dict(self):
        """Test that extras accepts dict values."""
        request = ServiceUpdateRequest(
            extras={"version": "1.0", "environment": "production"}
        )

        assert request.extras == {"version": "1.0", "environment": "production"}

    def test_extras_with_nested_dict(self):
        """Test that extras accepts nested dict values."""
        request = ServiceUpdateRequest(extras={"config": {"timeout": 30, "retries": 3}})

        assert request.extras == {"config": {"timeout": 30, "retries": 3}}

    def test_extras_can_be_none(self):
        """Test that extras can be None."""
        request = ServiceUpdateRequest(extras=None)

        assert request.extras is None

    def test_extras_can_be_empty_dict(self):
        """Test that extras can be empty dict."""
        request = ServiceUpdateRequest(extras={})

        assert request.extras == {}
