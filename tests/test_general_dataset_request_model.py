# tests/test_general_dataset_request_model.py
"""
Tests for GeneralDatasetRequest and related models.

Tests for api/models/general_dataset_request_model.py
"""

import pytest
from pydantic import ValidationError
from api.models.general_dataset_request_model import (
    ResourceRequest,
    GeneralDatasetRequest,
    GeneralDatasetUpdateRequest
)


class TestResourceRequest:
    """Tests for ResourceRequest model."""

    def test_create_with_required_fields(self):
        """Test creating ResourceRequest with required fields only."""
        resource = ResourceRequest(
            url="http://example.com/data.csv",
            name="test_resource"
        )

        assert resource.url == "http://example.com/data.csv"
        assert resource.name == "test_resource"
        assert resource.format is None
        assert resource.description is None
        assert resource.mimetype is None
        assert resource.size is None

    def test_create_with_all_fields(self):
        """Test creating ResourceRequest with all fields."""
        resource = ResourceRequest(
            url="https://api.example.com/data.json",
            name="complete_resource",
            format="JSON",
            description="A complete test resource",
            mimetype="application/json",
            size=2048
        )

        assert resource.url == "https://api.example.com/data.json"
        assert resource.name == "complete_resource"
        assert resource.format == "JSON"
        assert resource.description == "A complete test resource"
        assert resource.mimetype == "application/json"
        assert resource.size == 2048

    def test_missing_required_field_raises_error(self):
        """Test that missing required fields raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ResourceRequest(
                url="http://example.com/data.csv"
                # Missing name
            )

        errors = exc_info.value.errors()
        assert any(e["loc"][0] == "name" for e in errors)

    def test_create_with_various_formats(self):
        """Test ResourceRequest with various format values."""
        formats = ["CSV", "JSON", "XML", "NetCDF", "HDF5", "Parquet"]

        for fmt in formats:
            resource = ResourceRequest(
                url=f"http://example.com/data.{fmt.lower()}",
                name=f"resource_{fmt}",
                format=fmt
            )
            assert resource.format == fmt


class TestGeneralDatasetRequest:
    """Tests for GeneralDatasetRequest model."""

    def test_create_with_required_fields(self):
        """Test creating GeneralDatasetRequest with required fields only."""
        dataset = GeneralDatasetRequest(
            name="test_dataset",
            title="Test Dataset",
            owner_org="org-123"
        )

        assert dataset.name == "test_dataset"
        assert dataset.title == "Test Dataset"
        assert dataset.owner_org == "org-123"
        assert dataset.notes is None
        assert dataset.tags is None
        assert dataset.groups is None
        assert dataset.extras is None
        assert dataset.resources is None
        assert dataset.private is False
        assert dataset.license_id is None
        assert dataset.version is None

    def test_create_with_all_fields(self):
        """Test creating GeneralDatasetRequest with all fields."""
        resources = [
            ResourceRequest(url="http://ex.com/1", name="res1"),
            ResourceRequest(url="http://ex.com/2", name="res2")
        ]

        dataset = GeneralDatasetRequest(
            name="complete_dataset",
            title="Complete Dataset",
            owner_org="org-456",
            notes="A complete test dataset",
            tags=["climate", "data"],
            groups=["group1", "group2"],
            extras={"key1": "value1", "version": "2.0"},
            resources=resources,
            private=True,
            license_id="cc-by-4.0",
            version="1.0.0"
        )

        assert dataset.name == "complete_dataset"
        assert dataset.title == "Complete Dataset"
        assert dataset.owner_org == "org-456"
        assert dataset.notes == "A complete test dataset"
        assert dataset.tags == ["climate", "data"]
        assert dataset.groups == ["group1", "group2"]
        assert dataset.extras == {"key1": "value1", "version": "2.0"}
        assert len(dataset.resources) == 2
        assert dataset.private is True
        assert dataset.license_id == "cc-by-4.0"
        assert dataset.version == "1.0.0"

    def test_missing_required_field_raises_error(self):
        """Test that missing required fields raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            GeneralDatasetRequest(
                name="test",
                title="Test"
                # Missing owner_org
            )

        errors = exc_info.value.errors()
        assert any(e["loc"][0] == "owner_org" for e in errors)

    def test_with_multiple_resources(self):
        """Test GeneralDatasetRequest with multiple resources."""
        resources = [
            ResourceRequest(
                url=f"http://example.com/file{i}.csv",
                name=f"resource_{i}",
                format="CSV"
            )
            for i in range(5)
        ]

        dataset = GeneralDatasetRequest(
            name="multi_resource_dataset",
            title="Multi Resource Dataset",
            owner_org="org-789",
            resources=resources
        )

        assert len(dataset.resources) == 5
        assert dataset.resources[0].name == "resource_0"
        assert dataset.resources[4].name == "resource_4"

    def test_with_tags_list(self):
        """Test dataset with tags list."""
        dataset = GeneralDatasetRequest(
            name="tagged_dataset",
            title="Tagged Dataset",
            owner_org="org-123",
            tags=["climate", "weather", "temperature", "precipitation"]
        )

        assert len(dataset.tags) == 4
        assert "climate" in dataset.tags
        assert "precipitation" in dataset.tags

    def test_with_extras_dict(self):
        """Test dataset with extras metadata."""
        dataset = GeneralDatasetRequest(
            name="dataset_with_extras",
            title="Dataset With Extras",
            owner_org="org-456",
            extras={
                "spatial_coverage": "global",
                "temporal_coverage": "2020-2023",
                "update_frequency": "daily",
                "quality_score": 95
            }
        )

        assert dataset.extras["spatial_coverage"] == "global"
        assert dataset.extras["temporal_coverage"] == "2020-2023"
        assert dataset.extras["quality_score"] == 95

    def test_private_field_defaults_to_false(self):
        """Test that private field defaults to False."""
        dataset = GeneralDatasetRequest(
            name="test",
            title="Test",
            owner_org="org-123"
        )

        assert dataset.private is False

    def test_private_field_can_be_true(self):
        """Test that private field can be set to True."""
        dataset = GeneralDatasetRequest(
            name="test",
            title="Test",
            owner_org="org-123",
            private=True
        )

        assert dataset.private is True


class TestGeneralDatasetUpdateRequest:
    """Tests for GeneralDatasetUpdateRequest model."""

    def test_create_with_no_fields(self):
        """Test creating GeneralDatasetUpdateRequest with no fields (empty update)."""
        update = GeneralDatasetUpdateRequest()

        assert update.name is None
        assert update.title is None
        assert update.owner_org is None
        assert update.notes is None
        assert update.tags is None
        assert update.groups is None
        assert update.extras is None
        assert update.resources is None
        assert update.private is None
        assert update.license_id is None
        assert update.version is None

    def test_partial_update_with_single_field(self):
        """Test partial update with single field."""
        update = GeneralDatasetUpdateRequest(title="Updated Title")

        assert update.title == "Updated Title"
        assert update.name is None
        assert update.owner_org is None

    def test_partial_update_with_multiple_fields(self):
        """Test partial update with multiple fields."""
        update = GeneralDatasetUpdateRequest(
            title="Updated Title",
            notes="Updated description",
            tags=["new_tag"],
            private=True
        )

        assert update.title == "Updated Title"
        assert update.notes == "Updated description"
        assert update.tags == ["new_tag"]
        assert update.private is True

    def test_update_with_all_fields(self):
        """Test update with all fields."""
        resources = [
            ResourceRequest(url="http://ex.com/updated", name="updated_res")
        ]

        update = GeneralDatasetUpdateRequest(
            name="updated_dataset",
            title="Updated Dataset",
            owner_org="new-org-123",
            notes="Updated notes",
            tags=["updated", "tags"],
            groups=["new_group"],
            extras={"updated": "metadata"},
            resources=resources,
            private=False,
            license_id="mit",
            version="2.0.0"
        )

        assert update.name == "updated_dataset"
        assert update.title == "Updated Dataset"
        assert update.owner_org == "new-org-123"
        assert update.notes == "Updated notes"
        assert len(update.tags) == 2
        assert len(update.resources) == 1
        assert update.private is False
        assert update.license_id == "mit"
        assert update.version == "2.0.0"

    def test_update_tags_to_empty_list(self):
        """Test updating tags to empty list."""
        update = GeneralDatasetUpdateRequest(tags=[])

        assert update.tags == []

    def test_update_extras_to_new_dict(self):
        """Test updating extras to new dictionary."""
        update = GeneralDatasetUpdateRequest(
            extras={"new_key": "new_value", "another_key": 123}
        )

        assert update.extras["new_key"] == "new_value"
        assert update.extras["another_key"] == 123


class TestModelDictConversion:
    """Tests for model dict conversion."""

    def test_resource_request_model_dump(self):
        """Test ResourceRequest model_dump."""
        resource = ResourceRequest(
            url="http://example.com/data.csv",
            name="test_resource",
            format="CSV",
            description="Test",
            size=1024
        )

        data = resource.model_dump()
        assert data["url"] == "http://example.com/data.csv"
        assert data["name"] == "test_resource"
        assert data["format"] == "CSV"
        assert data["size"] == 1024

    def test_resource_request_model_dump_exclude_none(self):
        """Test ResourceRequest model_dump with exclude_none."""
        resource = ResourceRequest(
            url="http://example.com/data.csv",
            name="test_resource"
        )

        data = resource.model_dump(exclude_none=True)
        assert "url" in data
        assert "name" in data
        assert "format" not in data
        assert "description" not in data
        assert "mimetype" not in data
        assert "size" not in data

    def test_dataset_model_dump(self):
        """Test GeneralDatasetRequest model_dump."""
        dataset = GeneralDatasetRequest(
            name="test",
            title="Test Dataset",
            owner_org="org-123",
            tags=["tag1", "tag2"]
        )

        data = dataset.model_dump()
        assert data["name"] == "test"
        assert data["title"] == "Test Dataset"
        assert data["owner_org"] == "org-123"
        assert data["tags"] == ["tag1", "tag2"]

    def test_update_model_dump_exclude_none(self):
        """Test GeneralDatasetUpdateRequest model_dump with exclude_none."""
        update = GeneralDatasetUpdateRequest(
            title="Updated Title",
            notes="Updated notes"
        )

        data = update.model_dump(exclude_none=True)
        assert "title" in data
        assert "notes" in data
        assert "name" not in data
        assert "owner_org" not in data
        assert "tags" not in data


class TestNestedValidation:
    """Tests for nested resource validation."""

    def test_dataset_with_invalid_resource_raises_error(self):
        """Test that invalid nested resource raises ValidationError."""
        with pytest.raises(ValidationError):
            GeneralDatasetRequest(
                name="test",
                title="Test",
                owner_org="org-123",
                resources=[
                    {"url": "http://example.com"}  # Missing name
                ]
            )

    def test_dataset_with_valid_resource_dicts(self):
        """Test dataset creation with resource dicts instead of objects."""
        dataset = GeneralDatasetRequest(
            name="test",
            title="Test",
            owner_org="org-123",
            resources=[
                {"url": "http://ex.com/1", "name": "res1"},
                {"url": "http://ex.com/2", "name": "res2", "format": "CSV"}
            ]
        )

        assert len(dataset.resources) == 2
        assert dataset.resources[0].name == "res1"
        assert dataset.resources[1].format == "CSV"
