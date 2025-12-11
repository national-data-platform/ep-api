# tests/test_datasourceresponse_model.py
"""
Tests for DataSourceResponse and Resource models.

Tests for api/models/datasourceresponse_model.py
"""

import pytest
from pydantic import ValidationError
from api.models.datasourceresponse_model import Resource, DataSourceResponse


class TestResourceModel:
    """Tests for Resource model."""

    def test_create_resource_with_required_fields(self):
        """Test creating Resource with required fields."""
        resource = Resource(
            id="res-123",
            url="http://example.com/data.csv",
            name="Test Resource"
        )

        assert resource.id == "res-123"
        assert resource.url == "http://example.com/data.csv"
        assert resource.name == "Test Resource"
        assert resource.description is None
        assert resource.format is None

    def test_create_resource_with_all_fields(self):
        """Test creating Resource with all fields."""
        resource = Resource(
            id="res-456",
            url="https://api.example.com/data",
            name="Complete Resource",
            description="A complete test resource",
            format="JSON"
        )

        assert resource.id == "res-456"
        assert resource.url == "https://api.example.com/data"
        assert resource.name == "Complete Resource"
        assert resource.description == "A complete test resource"
        assert resource.format == "JSON"

    def test_create_resource_with_none_url(self):
        """Test creating Resource with None URL."""
        resource = Resource(
            id="res-789",
            url=None,
            name="Resource Without URL"
        )

        assert resource.url is None

    def test_resource_missing_required_field(self):
        """Test that missing required fields raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            Resource(
                id="res-123",
                url="http://example.com"
                # Missing name
            )

        errors = exc_info.value.errors()
        assert any(e["loc"][0] == "name" for e in errors)

    def test_resource_with_various_formats(self):
        """Test Resource with various format values."""
        formats = ["CSV", "JSON", "XML", "NetCDF", "HDF5"]

        for fmt in formats:
            resource = Resource(
                id=f"res-{fmt}",
                url="http://example.com/data",
                name="Test",
                format=fmt
            )
            assert resource.format == fmt


class TestDataSourceResponseModel:
    """Tests for DataSourceResponse model."""

    def test_create_with_required_fields(self):
        """Test creating DataSourceResponse with required fields."""
        resource = Resource(
            id="res-1",
            url="http://example.com/data.csv",
            name="Resource 1"
        )

        response = DataSourceResponse(
            id="ds-123",
            name="test_dataset",
            title="Test Dataset",
            resources=[resource]
        )

        assert response.id == "ds-123"
        assert response.name == "test_dataset"
        assert response.title == "Test Dataset"
        assert len(response.resources) == 1
        assert response.organization_id is None
        assert response.description is None
        assert response.extras is None

    def test_create_with_all_fields(self):
        """Test creating DataSourceResponse with all fields."""
        resources = [
            Resource(id="res-1", url="http://ex.com/1", name="Res 1"),
            Resource(id="res-2", url="http://ex.com/2", name="Res 2")
        ]

        response = DataSourceResponse(
            id="ds-456",
            name="complete_dataset",
            title="Complete Dataset",
            organization_id="org-789",
            description="A complete test dataset",
            resources=resources,
            extras={"key1": "value1", "version": "1.0"}
        )

        assert response.id == "ds-456"
        assert response.name == "complete_dataset"
        assert response.title == "Complete Dataset"
        assert response.organization_id == "org-789"
        assert response.description == "A complete test dataset"
        assert len(response.resources) == 2
        assert response.extras == {"key1": "value1", "version": "1.0"}

    def test_create_with_multiple_resources(self):
        """Test creating DataSourceResponse with multiple resources."""
        resources = [
            Resource(id=f"res-{i}", url=f"http://ex.com/{i}", name=f"Resource {i}")
            for i in range(5)
        ]

        response = DataSourceResponse(
            id="ds-multi",
            name="multi_resource_dataset",
            title="Multi Resource Dataset",
            resources=resources
        )

        assert len(response.resources) == 5
        assert response.resources[0].name == "Resource 0"
        assert response.resources[4].name == "Resource 4"

    def test_missing_required_field(self):
        """Test that missing required fields raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            DataSourceResponse(
                id="ds-123",
                name="test"
                # Missing title and resources
            )

        errors = exc_info.value.errors()
        field_names = [e["loc"][0] for e in errors]
        assert "title" in field_names
        assert "resources" in field_names

    def test_empty_resources_list(self):
        """Test creating DataSourceResponse with empty resources list."""
        response = DataSourceResponse(
            id="ds-empty",
            name="empty_dataset",
            title="Empty Dataset",
            resources=[]
        )

        assert len(response.resources) == 0


class TestDataSourceResponseAliases:
    """Tests for field aliases in DataSourceResponse."""

    def test_owner_org_alias(self):
        """Test that owner_org alias works for organization_id."""
        resource = Resource(id="res-1", url="http://ex.com", name="Res")

        response = DataSourceResponse(
            id="ds-123",
            name="test",
            title="Test",
            owner_org="org-456",  # Using alias
            resources=[resource]
        )

        assert response.organization_id == "org-456"

    def test_notes_alias(self):
        """Test that notes alias works for description."""
        resource = Resource(id="res-1", url="http://ex.com", name="Res")

        response = DataSourceResponse(
            id="ds-123",
            name="test",
            title="Test",
            notes="Test notes",  # Using alias
            resources=[resource]
        )

        assert response.description == "Test notes"

    def test_populate_by_name_allows_both(self):
        """Test that populate_by_name allows using both alias and field name."""
        resource = Resource(id="res-1", url="http://ex.com", name="Res")

        # Using field name
        response1 = DataSourceResponse(
            id="ds-1",
            name="test1",
            title="Test 1",
            organization_id="org-1",
            description="Desc 1",
            resources=[resource]
        )

        # Using alias
        response2 = DataSourceResponse(
            id="ds-2",
            name="test2",
            title="Test 2",
            owner_org="org-2",
            notes="Desc 2",
            resources=[resource]
        )

        assert response1.organization_id == "org-1"
        assert response1.description == "Desc 1"
        assert response2.organization_id == "org-2"
        assert response2.description == "Desc 2"


class TestDataSourceResponseExtras:
    """Tests for extras field in DataSourceResponse."""

    def test_extras_with_nested_dict(self):
        """Test extras with nested dictionary."""
        resource = Resource(id="res-1", url="http://ex.com", name="Res")

        response = DataSourceResponse(
            id="ds-123",
            name="test",
            title="Test",
            resources=[resource],
            extras={
                "mapping": {
                    "field1": "value1",
                    "field2": "value2"
                },
                "processing": {
                    "data_key": "key1",
                    "info_key": "key2"
                }
            }
        )

        assert "mapping" in response.extras
        assert response.extras["mapping"]["field1"] == "value1"
        assert response.extras["processing"]["data_key"] == "key1"

    def test_extras_with_various_types(self):
        """Test extras can contain various data types."""
        resource = Resource(id="res-1", url="http://ex.com", name="Res")

        response = DataSourceResponse(
            id="ds-123",
            name="test",
            title="Test",
            resources=[resource],
            extras={
                "string": "value",
                "number": 42,
                "float": 3.14,
                "boolean": True,
                "list": [1, 2, 3],
                "nested": {"key": "value"}
            }
        )

        assert response.extras["string"] == "value"
        assert response.extras["number"] == 42
        assert response.extras["float"] == 3.14
        assert response.extras["boolean"] is True
        assert response.extras["list"] == [1, 2, 3]
        assert response.extras["nested"]["key"] == "value"

    def test_empty_extras_dict(self):
        """Test DataSourceResponse with empty extras dict."""
        resource = Resource(id="res-1", url="http://ex.com", name="Res")

        response = DataSourceResponse(
            id="ds-123",
            name="test",
            title="Test",
            resources=[resource],
            extras={}
        )

        assert response.extras == {}


class TestModelDictConversion:
    """Tests for model dict conversion."""

    def test_resource_model_dump(self):
        """Test Resource model_dump."""
        resource = Resource(
            id="res-123",
            url="http://example.com",
            name="Test Resource",
            description="Test",
            format="CSV"
        )

        data = resource.model_dump()
        assert data["id"] == "res-123"
        assert data["url"] == "http://example.com"
        assert data["name"] == "Test Resource"
        assert data["description"] == "Test"
        assert data["format"] == "CSV"

    def test_resource_model_dump_exclude_none(self):
        """Test Resource model_dump with exclude_none."""
        resource = Resource(
            id="res-123",
            url="http://example.com",
            name="Test Resource"
        )

        data = resource.model_dump(exclude_none=True)
        assert "id" in data
        assert "name" in data
        assert "description" not in data
        assert "format" not in data

    def test_datasource_model_dump(self):
        """Test DataSourceResponse model_dump."""
        resource = Resource(id="res-1", url="http://ex.com", name="Res")

        response = DataSourceResponse(
            id="ds-123",
            name="test",
            title="Test Dataset",
            organization_id="org-456",
            resources=[resource]
        )

        data = response.model_dump()
        assert data["id"] == "ds-123"
        assert data["name"] == "test"
        assert data["title"] == "Test Dataset"
        assert data["organization_id"] == "org-456"
        assert len(data["resources"]) == 1

    def test_datasource_model_dump_by_alias(self):
        """Test DataSourceResponse model_dump with by_alias."""
        resource = Resource(id="res-1", url="http://ex.com", name="Res")

        response = DataSourceResponse(
            id="ds-123",
            name="test",
            title="Test",
            organization_id="org-456",
            description="Test desc",
            resources=[resource]
        )

        data = response.model_dump(by_alias=True)
        # Check that aliases are used in output
        assert "owner_org" in data or "organization_id" in data
        assert "notes" in data or "description" in data


class TestResourceNested:
    """Tests for nested Resource objects in DataSourceResponse."""

    def test_resources_preserve_properties(self):
        """Test that resource properties are preserved when nested."""
        resources = [
            Resource(
                id="res-1",
                url="http://ex.com/1",
                name="Resource 1",
                description="First resource",
                format="CSV"
            ),
            Resource(
                id="res-2",
                url="http://ex.com/2",
                name="Resource 2",
                description="Second resource",
                format="JSON"
            )
        ]

        response = DataSourceResponse(
            id="ds-123",
            name="test",
            title="Test",
            resources=resources
        )

        assert response.resources[0].id == "res-1"
        assert response.resources[0].format == "CSV"
        assert response.resources[1].id == "res-2"
        assert response.resources[1].format == "JSON"

    def test_resource_validation_within_datasource(self):
        """Test that Resource validation happens when creating DataSourceResponse."""
        with pytest.raises(ValidationError):
            DataSourceResponse(
                id="ds-123",
                name="test",
                title="Test",
                resources=[
                    {"id": "res-1", "url": "http://ex.com"}  # Missing name
                ]
            )
