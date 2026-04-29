# tests/test_general_dataset.py
import re
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from api.services.dataset_services.general_dataset import (
    RESERVED_KEYS,
    create_general_dataset,
    patch_general_dataset,
    update_general_dataset,
)


def test_reserved_keys_constant():
    """Test that RESERVED_KEYS constant contains expected keys."""
    expected_keys = {
        "name",
        "title",
        "owner_org",
        "notes",
        "id",
        "resources",
        "tags",
        "private",
        "license_id",
        "version",
        "state",
        "created",
        "last_modified",
        "url",
    }
    assert RESERVED_KEYS == expected_keys


class TestCreateGeneralDataset:
    """Test cases for create_general_dataset function."""

    def test_create_minimal_dataset(self):
        """Test creating dataset with minimal required parameters."""
        # Setup mock repository
        mock_repo = MagicMock()
        mock_repo.package_create.return_value = {"id": "dataset-123"}

        result = create_general_dataset(
            name="test_dataset",
            title="Test Dataset",
            owner_org="test_org",
            repository=mock_repo,
        )

        assert result == {
            "id": "dataset-123",
            "name": "test_dataset",
            "title": "Test Dataset",
            "warning": None,
        }
        mock_repo.package_create.assert_called_once()

        # Verify the call arguments
        call_args = mock_repo.package_create.call_args[1]
        assert call_args["name"] == "test_dataset"
        assert call_args["title"] == "Test Dataset"
        assert call_args["owner_org"] == "test_org"
        assert call_args["private"] is False

    def test_create_complete_dataset(self):
        """Test creating dataset with all parameters."""
        # Setup mock repository
        mock_repo = MagicMock()
        mock_repo.package_create.return_value = {"id": "dataset-456"}
        mock_repo.resource_create.return_value = None

        result = create_general_dataset(
            name="complete_dataset",
            title="Complete Dataset",
            owner_org="test_org",
            notes="This is a complete dataset",
            tags=["tag1", "tag2"],
            groups=["group1"],
            extras={"custom_field": "custom_value"},
            resources=[{"url": "http://example.com/data.csv", "name": "data"}],
            private=True,
            license_id="mit",
            version="1.0",
            repository=mock_repo,
        )

        assert result == {
            "id": "dataset-456",
            "name": "complete_dataset",
            "title": "Complete Dataset",
            "warning": None,
        }

        # Verify package_create call
        package_call = mock_repo.package_create.call_args[1]
        assert package_call["notes"] == "This is a complete dataset"
        assert package_call["private"] is True
        assert package_call["license_id"] == "mit"
        assert package_call["version"] == "1.0"
        assert package_call["tags"] == [{"name": "tag1"}, {"name": "tag2"}]
        assert package_call["groups"] == [{"name": "group1"}]
        assert len(package_call["extras"]) == 1
        assert package_call["extras"][0]["key"] == "custom_field"

        # Verify resource_create was called
        mock_repo.resource_create.assert_called_once()
        resource_call = mock_repo.resource_create.call_args[1]
        assert resource_call["package_id"] == "dataset-456"
        assert resource_call["url"] == "http://example.com/data.csv"

    def test_create_custom_ckan_instance(self):
        """Test creating dataset with custom repository."""
        custom_repo = MagicMock()
        custom_repo.package_create.return_value = {"id": "custom-789"}

        result = create_general_dataset(
            name="custom_dataset",
            title="Custom Dataset",
            owner_org="test_org",
            repository=custom_repo,
        )

        assert result == {
            "id": "custom-789",
            "name": "custom_dataset",
            "title": "Custom Dataset",
            "warning": None,
        }
        custom_repo.package_create.assert_called_once()

    def test_create_invalid_extras_type(self):
        """Test creating dataset with invalid extras type."""
        mock_repo = MagicMock()
        with pytest.raises(ValueError, match="Extras must be a dictionary or None"):
            create_general_dataset(
                name="invalid_dataset",
                title="Invalid Dataset",
                owner_org="test_org",
                extras="invalid_extras",
                repository=mock_repo,
            )

    def test_create_reserved_keys_in_extras(self):
        """Test creating dataset with reserved keys in extras."""
        mock_repo = MagicMock()
        with pytest.raises(KeyError, match="Extras contain reserved keys"):
            create_general_dataset(
                name="reserved_dataset",
                title="Reserved Dataset",
                owner_org="test_org",
                extras={"name": "reserved", "custom": "allowed"},
                repository=mock_repo,
            )

    def test_create_package_creation_error(self):
        """Test handling package creation errors."""
        mock_repo = MagicMock()
        mock_repo.package_create.side_effect = Exception("Package creation failed")

        with pytest.raises(Exception, match="Error creating general dataset"):
            create_general_dataset(
                name="error_dataset",
                title="Error Dataset",
                owner_org="test_org",
                repository=mock_repo,
            )

    def test_create_resource_creation_error(self):
        """Test handling resource creation errors."""
        mock_repo = MagicMock()
        mock_repo.package_create.return_value = {"id": "dataset-123"}
        mock_repo.resource_create.side_effect = Exception("Resource creation failed")

        with pytest.raises(Exception, match="Error creating dataset resources"):
            create_general_dataset(
                name="resource_error_dataset",
                title="Resource Error Dataset",
                owner_org="test_org",
                resources=[{"url": "http://example.com/data.csv"}],
                repository=mock_repo,
            )

    def test_create_without_optional_fields(self):
        """Test creating dataset without optional fields."""
        mock_repo = MagicMock()
        mock_repo.package_create.return_value = {"id": "minimal-123"}

        result = create_general_dataset(
            name="minimal_dataset",
            title="Minimal Dataset",
            owner_org="test_org",
            repository=mock_repo,
            # No optional fields provided
        )

        assert result == {
            "id": "minimal-123",
            "name": "minimal_dataset",
            "title": "Minimal Dataset",
            "warning": None,
        }

        # Verify only required fields are in the call
        call_args = mock_repo.package_create.call_args[1]
        assert "notes" not in call_args
        assert "license_id" not in call_args
        assert "version" not in call_args
        assert "tags" not in call_args
        assert "groups" not in call_args
        assert "extras" not in call_args

    def test_create_with_duplicate_name_auto_renames(self):
        """Duplicate name -> retry once with timestamp suffix and warn."""
        mock_repo = MagicMock()
        mock_repo.package_create.side_effect = [
            Exception("That name is already in use"),
            {"id": "dataset-renamed-123"},
        ]

        fixed_now = datetime(2026, 4, 29, 14, 30, 52)
        with patch(
            "api.services.dataset_services.general_dataset.datetime"
        ) as mock_datetime:
            mock_datetime.now.return_value = fixed_now
            mock_datetime.strftime = datetime.strftime

            result = create_general_dataset(
                name="my_dataset",
                title="My Dataset",
                owner_org="test_org",
                repository=mock_repo,
            )

        assert result == {
            "id": "dataset-renamed-123",
            "name": "my_dataset-20260429143052",
            "title": "My Dataset (2026-04-29 14:30:52)",
            "warning": (
                "A dataset named 'my_dataset' already exists. "
                "This dataset was saved as 'my_dataset-20260429143052' "
                "with title 'My Dataset (2026-04-29 14:30:52)'."
            ),
        }
        assert mock_repo.package_create.call_count == 2
        retry_call = mock_repo.package_create.call_args_list[1][1]
        assert retry_call["name"] == "my_dataset-20260429143052"
        assert retry_call["title"] == "My Dataset (2026-04-29 14:30:52)"
        # Generated slug must satisfy CKAN's name format constraints
        assert re.match(r"^[a-z0-9_-]+$", retry_call["name"])

    def test_create_with_duplicate_url_auto_renames(self):
        """Duplicate URL (slug) -> same retry-with-timestamp behavior."""
        mock_repo = MagicMock()
        mock_repo.package_create.side_effect = [
            Exception("That URL is already in use"),
            {"id": "dataset-renamed-456"},
        ]

        result = create_general_dataset(
            name="another_dataset",
            title="Another Dataset",
            owner_org="test_org",
            repository=mock_repo,
        )

        assert result["id"] == "dataset-renamed-456"
        assert result["name"].startswith("another_dataset-")
        assert result["title"].startswith("Another Dataset (")
        assert result["warning"] is not None
        assert "another_dataset" in result["warning"]
        assert mock_repo.package_create.call_count == 2

    def test_create_duplicate_retry_failure_propagates(self):
        """If the second attempt also fails, surface the retry error."""
        mock_repo = MagicMock()
        mock_repo.package_create.side_effect = [
            Exception("That name is already in use"),
            Exception("Some other catalog error"),
        ]

        with pytest.raises(
            Exception, match="Error creating general dataset: Some other catalog error"
        ):
            create_general_dataset(
                name="dup_dataset",
                title="Dup Dataset",
                owner_org="test_org",
                repository=mock_repo,
            )

    def test_create_non_duplicate_error_does_not_retry(self):
        """Non-duplicate errors must not trigger a second package_create call."""
        mock_repo = MagicMock()
        mock_repo.package_create.side_effect = Exception("Some unrelated CKAN error")

        with pytest.raises(
            Exception, match="Error creating general dataset: Some unrelated CKAN error"
        ):
            create_general_dataset(
                name="other_dataset",
                title="Other Dataset",
                owner_org="test_org",
                repository=mock_repo,
            )

        assert mock_repo.package_create.call_count == 1


class TestUpdateGeneralDataset:
    """Test cases for update_general_dataset function."""

    @pytest.fixture
    def sample_existing_dataset(self):
        """Sample existing dataset for update tests."""
        return {
            "id": "existing-123",
            "name": "existing_dataset",
            "title": "Existing Dataset",
            "owner_org": "existing_org",
            "notes": "Existing notes",
            "private": False,
            "extras": [{"key": "existing_key", "value": "existing_value"}],
        }

    def test_update_dataset_minimal(self, sample_existing_dataset):
        """Test updating dataset with minimal parameters."""
        mock_repo = MagicMock()
        mock_repo.package_show.return_value = sample_existing_dataset
        mock_repo.package_update.return_value = {"id": "existing-123"}

        result = update_general_dataset(
            dataset_id="existing-123", title="Updated Title", repository=mock_repo
        )

        assert result == "existing-123"
        mock_repo.package_show.assert_called_once_with(id="existing-123")
        mock_repo.package_update.assert_called_once()

        # Verify the update preserved existing values and updated title
        update_call = mock_repo.package_update.call_args[1]
        assert update_call["title"] == "Updated Title"
        assert update_call["name"] == "existing_dataset"  # Preserved

    def test_update_dataset_complete(self, sample_existing_dataset):
        """Test updating dataset with all parameters."""
        mock_repo = MagicMock()
        mock_repo.package_show.return_value = sample_existing_dataset
        mock_repo.package_update.return_value = {"id": "existing-123"}

        result = update_general_dataset(
            dataset_id="existing-123",
            name="updated_dataset",
            title="Updated Dataset",
            owner_org="updated_org",
            notes="Updated notes",
            tags=["new_tag"],
            groups=["new_group"],
            extras={"new_key": "new_value"},
            private=True,
            license_id="gpl",
            version="2.0",
            repository=mock_repo,
        )

        assert result == "existing-123"

        # Verify all fields were updated
        update_call = mock_repo.package_update.call_args[1]
        assert update_call["name"] == "updated_dataset"
        assert update_call["title"] == "Updated Dataset"
        assert update_call["owner_org"] == "updated_org"
        assert update_call["notes"] == "Updated notes"
        assert update_call["private"] is True
        assert update_call["license_id"] == "gpl"
        assert update_call["version"] == "2.0"
        assert update_call["tags"] == [{"name": "new_tag"}]
        assert update_call["groups"] == [{"name": "new_group"}]

        # Verify extras were merged
        extras_dict = {extra["key"]: extra["value"] for extra in update_call["extras"]}
        assert extras_dict["existing_key"] == "existing_value"  # Preserved
        assert extras_dict["new_key"] == "new_value"  # Added

    def test_update_fetch_error(self):
        """Test handling errors when fetching dataset for update."""
        mock_repo = MagicMock()
        mock_repo.package_show.side_effect = Exception("Dataset not found")

        with pytest.raises(Exception, match="Error fetching dataset"):
            update_general_dataset(dataset_id="nonexistent-123", repository=mock_repo)

    def test_update_package_update_error(self, sample_existing_dataset):
        """Test handling errors during package update."""
        mock_repo = MagicMock()
        mock_repo.package_show.return_value = sample_existing_dataset
        mock_repo.package_update.side_effect = Exception("Update failed")

        with pytest.raises(Exception, match="Error updating general dataset"):
            update_general_dataset(
                dataset_id="existing-123", title="Updated Title", repository=mock_repo
            )

    def test_update_invalid_extras(self):
        """Test updating with invalid extras."""
        mock_repo = MagicMock()
        with pytest.raises(ValueError, match="Extras must be a dictionary or None"):
            update_general_dataset(
                dataset_id="existing-123", extras="invalid_extras", repository=mock_repo
            )

    def test_update_reserved_keys_in_extras(self):
        """Test updating with reserved keys in extras."""
        mock_repo = MagicMock()
        with pytest.raises(KeyError, match="Extras contain reserved keys"):
            update_general_dataset(
                dataset_id="existing-123",
                extras={"id": "reserved", "custom": "allowed"},
                repository=mock_repo,
            )


class TestPatchGeneralDataset:
    """Test cases for patch_general_dataset function."""

    def test_patch_dataset(self):
        """Test patch_general_dataset delegates to update_general_dataset."""
        mock_repo = MagicMock()
        mock_repo.package_show.return_value = {
            "id": "patch-123",
            "name": "patch_dataset",
            "title": "Patch Dataset",
            "owner_org": "patch_org",
        }
        mock_repo.package_update.return_value = {"id": "patch-123"}

        # Patch should work exactly like update
        result = patch_general_dataset(
            dataset_id="patch-123", title="Patched Title", repository=mock_repo
        )

        assert result == "patch-123"
        mock_repo.package_show.assert_called_once()
        mock_repo.package_update.assert_called_once()

    def test_patch_with_custom_ckan_instance(self):
        """Test patch with custom repository."""
        custom_repo = MagicMock()
        custom_repo.package_show.return_value = {
            "id": "custom-patch-123",
            "name": "custom_patch_dataset",
            "title": "Custom Patch Dataset",
            "owner_org": "custom_org",
        }
        custom_repo.package_update.return_value = {"id": "custom-patch-123"}

        result = patch_general_dataset(
            dataset_id="custom-patch-123",
            title="Custom Patched Title",
            repository=custom_repo,
        )

        assert result == "custom-patch-123"
        custom_repo.package_show.assert_called_once()
        custom_repo.package_update.assert_called_once()

    def test_patch_with_all_field_types(self):
        """Test patch with all different field types to cover all branches."""
        mock_repo = MagicMock()
        mock_repo.package_show.return_value = {
            "id": "patch-all-123",
            "name": "old_name",
            "title": "Old Title",
            "owner_org": "old_org",
            "notes": "Old notes",
            "private": False,
            "license_id": "old-license",
            "version": "1.0",
            "tags": [],
            "groups": [],
            "extras": [],
            "resources": [],
        }
        mock_repo.package_update.return_value = {"id": "patch-all-123"}

        # Patch all fields to cover all conditional branches
        result = patch_general_dataset(
            dataset_id="patch-all-123",
            name="new_name",
            title="New Title",
            owner_org="new_org",
            notes="New notes",
            private=True,
            license_id="new-license",
            version="2.0",
            tags=["tag1", "tag2"],
            groups=["group1"],
            extras={"key1": "value1"},
            resources=[{"url": "http://example.com", "name": "resource1"}],
            repository=mock_repo,
        )

        assert result == "patch-all-123"
        mock_repo.package_show.assert_called_once()

        # Verify all fields were updated
        call_args = mock_repo.package_update.call_args
        updated_dataset = call_args[1] if call_args[1] else call_args[0][0]

        assert updated_dataset["name"] == "new_name"
        assert updated_dataset["title"] == "New Title"
        assert updated_dataset["owner_org"] == "new_org"
        assert updated_dataset["notes"] == "New notes"
        assert updated_dataset["private"] is True
        assert updated_dataset["license_id"] == "new-license"
        assert updated_dataset["version"] == "2.0"
        assert len(updated_dataset["tags"]) == 2
        assert len(updated_dataset["groups"]) == 1
        assert len(updated_dataset["extras"]) == 1
        assert len(updated_dataset["resources"]) == 1

    def test_patch_invalid_extras_type(self):
        """Test patch with invalid extras type."""
        mock_repo = MagicMock()

        with pytest.raises(ValueError, match="Extras must be a dictionary or None"):
            patch_general_dataset(
                dataset_id="patch-123",
                extras="not_a_dict",
                repository=mock_repo,
            )

    def test_patch_reserved_keys_in_extras(self):
        """Test patch with reserved keys in extras."""
        mock_repo = MagicMock()

        with pytest.raises(KeyError, match="Extras contain reserved keys"):
            patch_general_dataset(
                dataset_id="patch-123",
                extras={"name": "invalid", "custom": "valid"},
                repository=mock_repo,
            )

    def test_patch_fetch_error(self):
        """Test patch when fetching dataset fails."""
        mock_repo = MagicMock()
        mock_repo.package_show.side_effect = Exception("Dataset not found")

        with pytest.raises(Exception, match="Error fetching dataset"):
            patch_general_dataset(
                dataset_id="nonexistent-123",
                title="New Title",
                repository=mock_repo,
            )

    def test_patch_update_error(self):
        """Test patch when package update fails."""
        mock_repo = MagicMock()
        mock_repo.package_show.return_value = {
            "id": "patch-123",
            "name": "test_dataset",
            "title": "Test Dataset",
            "owner_org": "test_org",
        }
        mock_repo.package_update.side_effect = Exception("Update failed")

        with pytest.raises(Exception, match="Error updating general dataset"):
            patch_general_dataset(
                dataset_id="patch-123",
                title="New Title",
                repository=mock_repo,
            )

    def test_patch_with_resources_adding_new(self):
        """Test patch adding new resources."""
        mock_repo = MagicMock()
        mock_repo.package_show.return_value = {
            "id": "patch-res-123",
            "name": "test_dataset",
            "title": "Test Dataset",
            "owner_org": "test_org",
            "resources": [{"url": "http://existing.com", "name": "existing_resource"}],
        }
        mock_repo.package_update.return_value = {"id": "patch-res-123"}

        # Add a new resource
        result = patch_general_dataset(
            dataset_id="patch-res-123",
            resources=[{"url": "http://new.com", "name": "new_resource"}],
            repository=mock_repo,
        )

        assert result == "patch-res-123"

        call_args = mock_repo.package_update.call_args
        updated_dataset = call_args[1] if call_args[1] else call_args[0][0]

        # Should have both resources
        assert len(updated_dataset["resources"]) == 2

    def test_patch_with_resources_updating_existing_by_url(self):
        """Test patch updating existing resource by matching URL."""
        mock_repo = MagicMock()
        mock_repo.package_show.return_value = {
            "id": "patch-res-123",
            "name": "test_dataset",
            "title": "Test Dataset",
            "owner_org": "test_org",
            "resources": [
                {"url": "http://existing.com", "name": "old_name", "format": "CSV"}
            ],
        }
        mock_repo.package_update.return_value = {"id": "patch-res-123"}

        # Update existing resource by URL
        result = patch_general_dataset(
            dataset_id="patch-res-123",
            resources=[
                {"url": "http://existing.com", "name": "new_name", "format": "JSON"}
            ],
            repository=mock_repo,
        )

        assert result == "patch-res-123"

        call_args = mock_repo.package_update.call_args
        updated_dataset = call_args[1] if call_args[1] else call_args[0][0]

        # Should still have only one resource, but updated
        assert len(updated_dataset["resources"]) == 1
        assert updated_dataset["resources"][0]["name"] == "new_name"
        assert updated_dataset["resources"][0]["format"] == "JSON"

    def test_patch_with_resources_updating_existing_by_name(self):
        """Test patch updating existing resource by matching name."""
        mock_repo = MagicMock()
        mock_repo.package_show.return_value = {
            "id": "patch-res-123",
            "name": "test_dataset",
            "title": "Test Dataset",
            "owner_org": "test_org",
            "resources": [
                {"url": "http://old.com", "name": "same_name", "format": "CSV"}
            ],
        }
        mock_repo.package_update.return_value = {"id": "patch-res-123"}

        # Update existing resource by name
        result = patch_general_dataset(
            dataset_id="patch-res-123",
            resources=[
                {"url": "http://new.com", "name": "same_name", "format": "JSON"}
            ],
            repository=mock_repo,
        )

        assert result == "patch-res-123"

        call_args = mock_repo.package_update.call_args
        updated_dataset = call_args[1] if call_args[1] else call_args[0][0]

        # Should still have only one resource, but with updated URL
        assert len(updated_dataset["resources"]) == 1
        assert updated_dataset["resources"][0]["url"] == "http://new.com"
        assert updated_dataset["resources"][0]["format"] == "JSON"

    def test_patch_with_extras_merging(self):
        """Test patch merging new extras with existing ones."""
        mock_repo = MagicMock()
        mock_repo.package_show.return_value = {
            "id": "patch-extras-123",
            "name": "test_dataset",
            "title": "Test Dataset",
            "owner_org": "test_org",
            "extras": [
                {"key": "existing_key", "value": "existing_value"},
                {"key": "key_to_update", "value": "old_value"},
            ],
        }
        mock_repo.package_update.return_value = {"id": "patch-extras-123"}

        # Add new extra and update existing one
        result = patch_general_dataset(
            dataset_id="patch-extras-123",
            extras={"key_to_update": "new_value", "new_key": "new_value"},
            repository=mock_repo,
        )

        assert result == "patch-extras-123"

        call_args = mock_repo.package_update.call_args
        updated_dataset = call_args[1] if call_args[1] else call_args[0][0]

        extras_dict = {
            extra["key"]: extra["value"] for extra in updated_dataset["extras"]
        }

        # Should have all three extras
        assert len(extras_dict) == 3
        assert extras_dict["existing_key"] == "existing_value"
        assert extras_dict["key_to_update"] == "new_value"
        assert extras_dict["new_key"] == "new_value"

    def test_patch_default_repository(self):
        """Test patch uses default repository when none provided."""
        with patch(
            "api.services.dataset_services.general_dataset.catalog_settings"
        ) as mock_settings:
            mock_repo = MagicMock()
            mock_repo.package_show.return_value = {
                "id": "patch-default-123",
                "name": "test_dataset",
                "title": "Test Dataset",
                "owner_org": "test_org",
            }
            mock_repo.package_update.return_value = {"id": "patch-default-123"}
            mock_settings.local_catalog = mock_repo

            result = patch_general_dataset(
                dataset_id="patch-default-123",
                title="Updated Title",
            )

            assert result == "patch-default-123"
            mock_repo.package_show.assert_called_once()
            mock_repo.package_update.assert_called_once()
