# tests/test_general_dataset_response_model.py
"""
Tests for GeneralDatasetResponse and related models.

Tests for api/models/general_dataset_response_model.py
"""

import pytest
from pydantic import ValidationError
from api.models.general_dataset_response_model import (
    ResourceResponse,
    GeneralDatasetResponse,
)


class TestResourceResponse:
    """Tests for ResourceResponse model."""

    def test_create_with_required_fields(self):
        """Test creating ResourceResponse with required fields only."""
        resource = ResourceResponse(
            id="resource-123", url="http://example.com/data.csv", name="test_resource"
        )

        assert resource.id == "resource-123"
        assert resource.url == "http://example.com/data.csv"
        assert resource.name == "test_resource"
        assert resource.format is None
        assert resource.description is None
        assert resource.mimetype is None
        assert resource.size is None
        assert resource.created is None
        assert resource.last_modified is None

    def test_create_with_all_fields(self):
        """Test creating ResourceResponse with all fields."""
        resource = ResourceResponse(
            id="resource-456",
            url="https://api.example.com/data.json",
            name="complete_resource",
            format="JSON",
            description="A complete test resource",
            mimetype="application/json",
            size=2048,
            created="2023-01-01T00:00:00Z",
            last_modified="2023-06-01T12:00:00Z",
        )

        assert resource.id == "resource-456"
        assert resource.url == "https://api.example.com/data.json"
        assert resource.name == "complete_resource"
        assert resource.format == "JSON"
        assert resource.description == "A complete test resource"
        assert resource.mimetype == "application/json"
        assert resource.size == 2048
        assert resource.created == "2023-01-01T00:00:00Z"
        assert resource.last_modified == "2023-06-01T12:00:00Z"

    def test_missing_required_field_raises_error(self):
        """Test that missing required fields raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ResourceResponse(
                id="resource-123",
                url="http://example.com/data.csv",
                # Missing name
            )

        errors = exc_info.value.errors()
        assert any(e["loc"][0] == "name" for e in errors)

    def test_create_with_various_formats(self):
        """Test ResourceResponse with various format values."""
        formats = ["CSV", "JSON", "XML", "NetCDF", "HDF5", "Parquet"]

        for fmt in formats:
            resource = ResourceResponse(
                id=f"resource-{fmt}",
                url=f"http://example.com/data.{fmt.lower()}",
                name=f"resource_{fmt}",
                format=fmt,
            )
            assert resource.format == fmt

    def test_create_with_timestamps(self):
        """Test ResourceResponse with creation and modification timestamps."""
        resource = ResourceResponse(
            id="resource-789",
            url="http://example.com/data.nc",
            name="timestamped_resource",
            created="2023-01-15T10:30:00Z",
            last_modified="2023-07-20T15:45:30Z",
        )

        assert resource.created == "2023-01-15T10:30:00Z"
        assert resource.last_modified == "2023-07-20T15:45:30Z"


class TestGeneralDatasetResponse:
    """Tests for GeneralDatasetResponse model."""

    def test_create_with_required_fields(self):
        """Test creating GeneralDatasetResponse with required fields only."""
        dataset = GeneralDatasetResponse(
            id="dataset-123", name="test_dataset", title="Test Dataset"
        )

        assert dataset.id == "dataset-123"
        assert dataset.name == "test_dataset"
        assert dataset.title == "Test Dataset"
        assert dataset.owner_org is None
        assert dataset.notes is None
        assert dataset.tags is None
        assert dataset.groups is None
        assert dataset.extras is None
        assert dataset.resources is None
        assert dataset.private is None
        assert dataset.license_id is None
        assert dataset.version is None
        assert dataset.created is None
        assert dataset.last_modified is None
        assert dataset.url is None
        assert dataset.state is None

    def test_create_with_all_fields(self):
        """Test creating GeneralDatasetResponse with all fields."""
        resources = [
            ResourceResponse(id="res-1", url="http://ex.com/1", name="res1"),
            ResourceResponse(id="res-2", url="http://ex.com/2", name="res2"),
        ]

        dataset = GeneralDatasetResponse(
            id="dataset-456",
            name="complete_dataset",
            title="Complete Dataset",
            owner_org="org-789",
            notes="A complete test dataset",
            tags=["climate", "data"],
            groups=["group1", "group2"],
            extras={"key1": "value1", "version": "2.0"},
            resources=resources,
            private=True,
            license_id="cc-by-4.0",
            version="1.0.0",
            created="2023-01-01T00:00:00Z",
            last_modified="2023-06-01T00:00:00Z",
            url="https://catalog.example.com/dataset/complete_dataset",
            state="active",
        )

        assert dataset.id == "dataset-456"
        assert dataset.name == "complete_dataset"
        assert dataset.title == "Complete Dataset"
        assert dataset.owner_org == "org-789"
        assert dataset.notes == "A complete test dataset"
        assert dataset.tags == ["climate", "data"]
        assert dataset.groups == ["group1", "group2"]
        assert dataset.extras == {"key1": "value1", "version": "2.0"}
        assert len(dataset.resources) == 2
        assert dataset.private is True
        assert dataset.license_id == "cc-by-4.0"
        assert dataset.version == "1.0.0"
        assert dataset.created == "2023-01-01T00:00:00Z"
        assert dataset.last_modified == "2023-06-01T00:00:00Z"
        assert dataset.url == "https://catalog.example.com/dataset/complete_dataset"
        assert dataset.state == "active"

    def test_missing_required_field_raises_error(self):
        """Test that missing required fields raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            GeneralDatasetResponse(
                id="dataset-123",
                name="test",
                # Missing title
            )

        errors = exc_info.value.errors()
        assert any(e["loc"][0] == "title" for e in errors)

    def test_with_multiple_resources(self):
        """Test GeneralDatasetResponse with multiple resources."""
        resources = [
            ResourceResponse(
                id=f"resource-{i}",
                url=f"http://example.com/file{i}.csv",
                name=f"resource_{i}",
                format="CSV",
            )
            for i in range(5)
        ]

        dataset = GeneralDatasetResponse(
            id="dataset-multi",
            name="multi_resource_dataset",
            title="Multi Resource Dataset",
            resources=resources,
        )

        assert len(dataset.resources) == 5
        assert dataset.resources[0].name == "resource_0"
        assert dataset.resources[4].name == "resource_4"

    def test_with_tags_list(self):
        """Test dataset with tags list."""
        dataset = GeneralDatasetResponse(
            id="dataset-tagged",
            name="tagged_dataset",
            title="Tagged Dataset",
            tags=["climate", "weather", "temperature", "precipitation"],
        )

        assert len(dataset.tags) == 4
        assert "climate" in dataset.tags
        assert "precipitation" in dataset.tags

    def test_with_extras_dict(self):
        """Test dataset with extras metadata."""
        dataset = GeneralDatasetResponse(
            id="dataset-extras",
            name="dataset_with_extras",
            title="Dataset With Extras",
            extras={
                "spatial_coverage": "global",
                "temporal_coverage": "2020-2023",
                "update_frequency": "daily",
                "quality_score": 95,
            },
        )

        assert dataset.extras["spatial_coverage"] == "global"
        assert dataset.extras["temporal_coverage"] == "2020-2023"
        assert dataset.extras["quality_score"] == 95

    def test_with_state_values(self):
        """Test dataset with different state values."""
        states = ["active", "deleted", "draft"]

        for state in states:
            dataset = GeneralDatasetResponse(
                id=f"dataset-{state}",
                name=f"dataset_{state}",
                title=f"Dataset {state.title()}",
                state=state,
            )
            assert dataset.state == state

    def test_with_timestamps(self):
        """Test dataset with creation and modification timestamps."""
        dataset = GeneralDatasetResponse(
            id="dataset-timestamps",
            name="timestamped_dataset",
            title="Timestamped Dataset",
            created="2023-01-15T10:30:00Z",
            last_modified="2023-07-20T15:45:30Z",
        )

        assert dataset.created == "2023-01-15T10:30:00Z"
        assert dataset.last_modified == "2023-07-20T15:45:30Z"

    def test_with_url_field(self):
        """Test dataset with URL field."""
        dataset = GeneralDatasetResponse(
            id="dataset-url",
            name="dataset_with_url",
            title="Dataset With URL",
            url="https://catalog.example.com/dataset/my-dataset",
        )

        assert dataset.url == "https://catalog.example.com/dataset/my-dataset"


class TestModelDictConversion:
    """Tests for model dict conversion."""

    def test_resource_response_model_dump(self):
        """Test ResourceResponse model_dump."""
        resource = ResourceResponse(
            id="resource-123",
            url="http://example.com/data.csv",
            name="test_resource",
            format="CSV",
            description="Test",
            size=1024,
        )

        data = resource.model_dump()
        assert data["id"] == "resource-123"
        assert data["url"] == "http://example.com/data.csv"
        assert data["name"] == "test_resource"
        assert data["format"] == "CSV"
        assert data["size"] == 1024

    def test_resource_response_model_dump_exclude_none(self):
        """Test ResourceResponse model_dump with exclude_none."""
        resource = ResourceResponse(
            id="resource-123", url="http://example.com/data.csv", name="test_resource"
        )

        data = resource.model_dump(exclude_none=True)
        assert "id" in data
        assert "name" in data
        assert "url" in data
        assert "format" not in data
        assert "description" not in data
        assert "mimetype" not in data
        assert "size" not in data
        assert "created" not in data
        assert "last_modified" not in data

    def test_dataset_model_dump(self):
        """Test GeneralDatasetResponse model_dump."""
        dataset = GeneralDatasetResponse(
            id="dataset-123",
            name="test",
            title="Test Dataset",
            owner_org="org-456",
            tags=["tag1", "tag2"],
        )

        data = dataset.model_dump()
        assert data["id"] == "dataset-123"
        assert data["name"] == "test"
        assert data["title"] == "Test Dataset"
        assert data["owner_org"] == "org-456"
        assert data["tags"] == ["tag1", "tag2"]

    def test_dataset_model_dump_exclude_none(self):
        """Test GeneralDatasetResponse model_dump with exclude_none."""
        dataset = GeneralDatasetResponse(
            id="dataset-123", name="test", title="Test Dataset", owner_org="org-456"
        )

        data = dataset.model_dump(exclude_none=True)
        assert "id" in data
        assert "name" in data
        assert "title" in data
        assert "owner_org" in data
        assert "notes" not in data
        assert "tags" not in data
        assert "extras" not in data
        assert "resources" not in data


class TestNestedValidation:
    """Tests for nested resource validation."""

    def test_dataset_with_invalid_resource_raises_error(self):
        """Test that invalid nested resource raises ValidationError."""
        with pytest.raises(ValidationError):
            GeneralDatasetResponse(
                id="dataset-123",
                name="test",
                title="Test",
                resources=[
                    {"id": "res-1", "url": "http://example.com"}  # Missing name
                ],
            )

    def test_dataset_with_valid_resource_dicts(self):
        """Test dataset creation with resource dicts instead of objects."""
        dataset = GeneralDatasetResponse(
            id="dataset-123",
            name="test",
            title="Test",
            resources=[
                {"id": "res-1", "url": "http://ex.com/1", "name": "res1"},
                {
                    "id": "res-2",
                    "url": "http://ex.com/2",
                    "name": "res2",
                    "format": "CSV",
                },
            ],
        )

        assert len(dataset.resources) == 2
        assert dataset.resources[0].name == "res1"
        assert dataset.resources[1].format == "CSV"

    def test_resources_preserve_properties(self):
        """Test that resource properties are preserved when nested."""
        resources = [
            ResourceResponse(
                id="res-1",
                url="http://ex.com/1",
                name="Resource 1",
                description="First resource",
                format="CSV",
                size=1024,
                created="2023-01-01T00:00:00Z",
            ),
            ResourceResponse(
                id="res-2",
                url="http://ex.com/2",
                name="Resource 2",
                description="Second resource",
                format="JSON",
                size=2048,
                last_modified="2023-06-01T00:00:00Z",
            ),
        ]

        dataset = GeneralDatasetResponse(
            id="dataset-123", name="test", title="Test", resources=resources
        )

        assert dataset.resources[0].id == "res-1"
        assert dataset.resources[0].format == "CSV"
        assert dataset.resources[0].size == 1024
        assert dataset.resources[0].created == "2023-01-01T00:00:00Z"
        assert dataset.resources[1].id == "res-2"
        assert dataset.resources[1].format == "JSON"
        assert dataset.resources[1].size == 2048
        assert dataset.resources[1].last_modified == "2023-06-01T00:00:00Z"
