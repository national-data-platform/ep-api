# tests/test_kafka_update_service.py
import json
from unittest.mock import MagicMock, patch

import pytest

from api.services.kafka_services.update_kafka import patch_kafka, update_kafka


class TestUpdateKafka:
    """Test cases for update_kafka function."""

    @patch("api.services.kafka_services.update_kafka.ckan_settings")
    def test_update_kafka_success_all_params(self, mock_ckan_settings):
        """Test successful Kafka dataset update with all parameters."""
        # Mock CKAN instance and dataset data
        mock_ckan = MagicMock()
        mock_ckan_settings.ckan = mock_ckan
        
        existing_dataset = {
            "id": "kafka-dataset-123",
            "name": "old_kafka_dataset",
            "title": "Old Kafka Dataset",
            "owner_org": "test_org",
            "notes": "Old description",
            "extras": [
                {"key": "host", "value": "old-host.com"},
                {"key": "port", "value": "9092"},
                {"key": "topic", "value": "old_topic"},
                {"key": "existing_extra", "value": "existing_value"}
            ]
        }
        
        updated_dataset = existing_dataset.copy()
        updated_dataset["id"] = "kafka-dataset-123"
        
        mock_ckan.action.package_show.return_value = existing_dataset
        mock_ckan.action.package_update.return_value = updated_dataset

        mapping_data = {"field1": "kafka_field1", "field2": "kafka_field2"}
        processing_data = {"transform": "uppercase", "filter": "non_empty"}

        result = update_kafka(
            dataset_id="kafka-dataset-123",
            dataset_name="new_kafka_dataset",
            dataset_title="New Kafka Dataset",
            owner_org="new_org",
            kafka_topic="new_topic",
            kafka_host="new-host.com",
            kafka_port="9093",
            dataset_description="New description",
            extras={"custom_field": "custom_value"},
            mapping=mapping_data,
            processing=processing_data
        )

        assert result == "kafka-dataset-123"
        mock_ckan.action.package_show.assert_called_once_with(id="kafka-dataset-123")
        mock_ckan.action.package_update.assert_called_once()

        # Verify the update call contains expected data
        update_call_args = mock_ckan.action.package_update.call_args[1]
        assert update_call_args["name"] == "new_kafka_dataset"
        assert update_call_args["title"] == "New Kafka Dataset"
        assert update_call_args["owner_org"] == "new_org"
        assert update_call_args["notes"] == "New description"

        # Verify extras contain all expected values
        extras_dict = {extra["key"]: extra["value"] for extra in update_call_args["extras"]}
        assert extras_dict["host"] == "new-host.com"
        assert extras_dict["port"] == "9093"
        assert extras_dict["topic"] == "new_topic"
        assert extras_dict["mapping"] == json.dumps(mapping_data)
        assert extras_dict["processing"] == json.dumps(processing_data)
        assert extras_dict["custom_field"] == "custom_value"
        assert extras_dict["existing_extra"] == "existing_value"  # Preserved

    @patch("api.services.kafka_services.update_kafka.ckan_settings")
    def test_update_kafka_with_custom_ckan_instance(self, mock_ckan_settings):
        """Test update_kafka with custom CKAN instance."""
        custom_ckan = MagicMock()
        existing_dataset = {
            "id": "kafka-dataset-123",
            "name": "test_kafka",
            "title": "Test Kafka",
            "owner_org": "test_org",
            "extras": []
        }
        
        custom_ckan.action.package_show.return_value = existing_dataset
        custom_ckan.action.package_update.return_value = existing_dataset

        result = update_kafka(
            dataset_id="kafka-dataset-123",
            dataset_name="updated_kafka",
            ckan_instance=custom_ckan
        )

        assert result == "kafka-dataset-123"
        custom_ckan.action.package_show.assert_called_once_with(id="kafka-dataset-123")
        # Should not use default ckan_settings.ckan
        mock_ckan_settings.ckan.action.package_show.assert_not_called()

    @patch("api.services.kafka_services.update_kafka.ckan_settings")
    def test_update_kafka_reserved_keys_error(self, mock_ckan_settings):
        """Test update_kafka with reserved keys in extras."""
        mock_ckan = MagicMock()
        mock_ckan_settings.ckan = mock_ckan
        
        existing_dataset = {
            "id": "kafka-dataset-123",
            "name": "test_kafka",
            "title": "Test Kafka",
            "owner_org": "test_org",
            "extras": []
        }
        
        mock_ckan.action.package_show.return_value = existing_dataset

        with pytest.raises(KeyError, match="Extras contain reserved keys"):
            update_kafka(
                dataset_id="kafka-dataset-123",
                extras={"name": "invalid", "port": "invalid", "custom": "valid"}
            )

    @patch("api.services.kafka_services.update_kafka.ckan_settings")
    def test_update_kafka_fetch_error(self, mock_ckan_settings):
        """Test update_kafka when fetching dataset fails."""
        mock_ckan = MagicMock()
        mock_ckan_settings.ckan = mock_ckan
        mock_ckan.action.package_show.side_effect = Exception("Dataset not found")

        with pytest.raises(Exception, match="Error fetching Kafka dataset: Dataset not found"):
            update_kafka(dataset_id="nonexistent-dataset")

    @patch("api.services.kafka_services.update_kafka.ckan_settings")
    def test_update_kafka_update_error(self, mock_ckan_settings):
        """Test update_kafka when updating dataset fails."""
        mock_ckan = MagicMock()
        mock_ckan_settings.ckan = mock_ckan
        
        existing_dataset = {
            "id": "kafka-dataset-123",
            "name": "test_kafka",
            "title": "Test Kafka",
            "owner_org": "test_org",
            "extras": []
        }
        
        mock_ckan.action.package_show.return_value = existing_dataset
        mock_ckan.action.package_update.side_effect = Exception("Update failed")

        with pytest.raises(Exception, match="Error updating Kafka dataset: Update failed"):
            update_kafka(dataset_id="kafka-dataset-123", dataset_name="new_name")

    @patch("api.services.kafka_services.update_kafka.ckan_settings")
    def test_update_kafka_partial_kafka_params(self, mock_ckan_settings):
        """Test update_kafka with partial Kafka-specific parameters."""
        mock_ckan = MagicMock()
        mock_ckan_settings.ckan = mock_ckan
        
        existing_dataset = {
            "id": "kafka-dataset-123",
            "name": "test_kafka",
            "title": "Test Kafka",
            "owner_org": "test_org",
            "extras": [
                {"key": "host", "value": "old-host.com"},
                {"key": "port", "value": "9092"},
                {"key": "topic", "value": "old_topic"}
            ]
        }
        
        mock_ckan.action.package_show.return_value = existing_dataset
        mock_ckan.action.package_update.return_value = existing_dataset

        result = update_kafka(
            dataset_id="kafka-dataset-123",
            kafka_host="new-host.com"  # Only update host
        )

        assert result == "kafka-dataset-123"
        
        # Verify only host was updated, others preserved
        update_call_args = mock_ckan.action.package_update.call_args[1]
        extras_dict = {extra["key"]: extra["value"] for extra in update_call_args["extras"]}
        assert extras_dict["host"] == "new-host.com"  # Updated
        assert extras_dict["port"] == "9092"  # Preserved
        assert extras_dict["topic"] == "old_topic"  # Preserved

    @patch("api.services.kafka_services.update_kafka.ckan_settings")
    def test_update_kafka_no_extras_provided(self, mock_ckan_settings):
        """Test update_kafka without extras but with other parameters."""
        mock_ckan = MagicMock()
        mock_ckan_settings.ckan = mock_ckan
        
        existing_dataset = {
            "id": "kafka-dataset-123",
            "name": "test_kafka",
            "title": "Test Kafka",
            "owner_org": "test_org",
            "extras": [{"key": "existing", "value": "preserved"}]
        }
        
        mock_ckan.action.package_show.return_value = existing_dataset
        mock_ckan.action.package_update.return_value = existing_dataset

        result = update_kafka(
            dataset_id="kafka-dataset-123",
            dataset_name="updated_kafka",
            kafka_topic="new_topic"
        )

        assert result == "kafka-dataset-123"
        
        # Verify existing extras are preserved and new Kafka params added
        update_call_args = mock_ckan.action.package_update.call_args[1]
        extras_dict = {extra["key"]: extra["value"] for extra in update_call_args["extras"]}
        assert extras_dict["existing"] == "preserved"
        assert extras_dict["topic"] == "new_topic"


class TestPatchKafka:
    """Test cases for patch_kafka function."""

    @patch("api.services.kafka_services.update_kafka.ckan_settings")
    def test_patch_kafka_success(self, mock_ckan_settings):
        """Test successful Kafka dataset patch with partial updates."""
        mock_ckan = MagicMock()
        mock_ckan_settings.ckan = mock_ckan
        
        existing_dataset = {
            "id": "kafka-dataset-123",
            "name": "existing_kafka",
            "title": "Existing Kafka Dataset",
            "owner_org": "test_org",
            "notes": "Existing description",
            "extras": [
                {"key": "host", "value": "existing-host.com"},
                {"key": "port", "value": "9092"},
                {"key": "existing_extra", "value": "existing_value"}
            ]
        }
        
        mock_ckan.action.package_show.return_value = existing_dataset
        mock_ckan.action.package_update.return_value = existing_dataset

        mapping_data = {"new_field": "new_kafka_field"}
        
        result = patch_kafka(
            dataset_id="kafka-dataset-123",
            dataset_title="Updated Kafka Dataset",
            kafka_host="new-host.com",
            mapping=mapping_data,
            extras={"new_field": "new_value"}
        )

        assert result == "kafka-dataset-123"
        mock_ckan.action.package_show.assert_called_once_with(id="kafka-dataset-123")
        
        # Verify only specified fields were updated
        update_call_args = mock_ckan.action.package_update.call_args[1]
        assert update_call_args["name"] == "existing_kafka"  # Unchanged
        assert update_call_args["title"] == "Updated Kafka Dataset"  # Changed
        assert update_call_args["notes"] == "Existing description"  # Unchanged
        
        # Verify extras were merged correctly
        extras_dict = {extra["key"]: extra["value"] for extra in update_call_args["extras"]}
        assert extras_dict["host"] == "new-host.com"  # Updated
        assert extras_dict["port"] == "9092"  # Preserved
        assert extras_dict["existing_extra"] == "existing_value"  # Preserved
        assert extras_dict["mapping"] == json.dumps(mapping_data)  # Added
        assert extras_dict["new_field"] == "new_value"  # Added

    @patch("api.services.kafka_services.update_kafka.ckan_settings")
    def test_patch_kafka_reserved_keys_error(self, mock_ckan_settings):
        """Test patch_kafka with reserved keys in extras."""
        mock_ckan = MagicMock()
        mock_ckan_settings.ckan = mock_ckan
        
        existing_dataset = {
            "id": "kafka-dataset-123",
            "name": "test_kafka",
            "title": "Test Kafka",
            "owner_org": "test_org",
            "extras": []
        }
        
        mock_ckan.action.package_show.return_value = existing_dataset

        with pytest.raises(KeyError, match="Extras contain reserved keys"):
            patch_kafka(
                dataset_id="kafka-dataset-123",
                extras={"id": "invalid", "mapping": "also_invalid"}
            )

    @patch("api.services.kafka_services.update_kafka.ckan_settings")
    def test_patch_kafka_fetch_error(self, mock_ckan_settings):
        """Test patch_kafka when fetching dataset fails."""
        mock_ckan = MagicMock()
        mock_ckan_settings.ckan = mock_ckan
        mock_ckan.action.package_show.side_effect = Exception("Dataset not found")

        with pytest.raises(Exception, match="Error fetching Kafka dataset: Dataset not found"):
            patch_kafka(dataset_id="nonexistent-dataset", dataset_title="New Title")

    @patch("api.services.kafka_services.update_kafka.ckan_settings")
    def test_patch_kafka_update_error(self, mock_ckan_settings):
        """Test patch_kafka when updating dataset fails."""
        mock_ckan = MagicMock()
        mock_ckan_settings.ckan = mock_ckan
        
        existing_dataset = {
            "id": "kafka-dataset-123",
            "name": "test_kafka",
            "title": "Test Kafka",
            "owner_org": "test_org",
            "extras": []
        }
        
        mock_ckan.action.package_show.return_value = existing_dataset
        mock_ckan.action.package_update.side_effect = Exception("Update failed")

        with pytest.raises(Exception, match="Error updating Kafka dataset: Update failed"):
            patch_kafka(dataset_id="kafka-dataset-123", dataset_title="New Title")

    @patch("api.services.kafka_services.update_kafka.ckan_settings")
    def test_patch_kafka_all_kafka_params(self, mock_ckan_settings):
        """Test patch_kafka with all Kafka-specific parameters."""
        mock_ckan = MagicMock()
        mock_ckan_settings.ckan = mock_ckan
        
        existing_dataset = {
            "id": "kafka-dataset-123",
            "name": "test_kafka",
            "title": "Test Kafka",
            "owner_org": "test_org",
            "extras": [{"key": "existing", "value": "preserved"}]
        }
        
        mock_ckan.action.package_show.return_value = existing_dataset
        mock_ckan.action.package_update.return_value = existing_dataset

        mapping_data = {"field1": "kafka1"}
        processing_data = {"filter": "active"}

        result = patch_kafka(
            dataset_id="kafka-dataset-123",
            kafka_host="patch-host.com",
            kafka_port="9094",
            kafka_topic="patch_topic",
            mapping=mapping_data,
            processing=processing_data
        )

        assert result == "kafka-dataset-123"
        
        # Verify all Kafka-specific fields were added/updated
        update_call_args = mock_ckan.action.package_update.call_args[1]
        extras_dict = {extra["key"]: extra["value"] for extra in update_call_args["extras"]}
        assert extras_dict["host"] == "patch-host.com"
        assert extras_dict["port"] == "9094"
        assert extras_dict["topic"] == "patch_topic"
        assert extras_dict["mapping"] == json.dumps(mapping_data)
        assert extras_dict["processing"] == json.dumps(processing_data)
        assert extras_dict["existing"] == "preserved"  # Original preserved

    @patch("api.services.kafka_services.update_kafka.ckan_settings")
    def test_patch_kafka_no_changes(self, mock_ckan_settings):
        """Test patch_kafka with no actual changes (all None parameters)."""
        mock_ckan = MagicMock()
        mock_ckan_settings.ckan = mock_ckan
        
        existing_dataset = {
            "id": "kafka-dataset-123",
            "name": "test_kafka",
            "title": "Test Kafka",
            "owner_org": "test_org",
            "extras": [{"key": "existing", "value": "value"}]
        }
        
        mock_ckan.action.package_show.return_value = existing_dataset
        mock_ckan.action.package_update.return_value = existing_dataset

        result = patch_kafka(dataset_id="kafka-dataset-123")

        assert result == "kafka-dataset-123"
        
        # Verify dataset structure is preserved
        update_call_args = mock_ckan.action.package_update.call_args[1]
        assert update_call_args["name"] == "test_kafka"
        assert update_call_args["title"] == "Test Kafka"
        assert len(update_call_args["extras"]) == 1
        assert update_call_args["extras"][0]["key"] == "existing"

    @patch("api.services.kafka_services.update_kafka.ckan_settings")
    def test_patch_kafka_individual_fields(self, mock_ckan_settings):
        """Test patch_kafka updating individual fields separately."""
        mock_ckan = MagicMock()
        mock_ckan_settings.ckan = mock_ckan
        
        existing_dataset = {
            "id": "kafka-dataset-123",
            "name": "test_kafka",
            "title": "Test Kafka",
            "owner_org": "test_org",
            "notes": "old notes",
            "extras": []
        }
        
        mock_ckan.action.package_show.return_value = existing_dataset
        mock_ckan.action.package_update.return_value = existing_dataset

        result = patch_kafka(
            dataset_id="kafka-dataset-123",
            dataset_name="patched_kafka",
            owner_org="new_org",
            dataset_description="patched description"
        )

        assert result == "kafka-dataset-123"
        
        # Verify individual field updates
        update_call_args = mock_ckan.action.package_update.call_args[1]
        assert update_call_args["name"] == "patched_kafka"  # Updated
        assert update_call_args["title"] == "Test Kafka"  # Unchanged
        assert update_call_args["owner_org"] == "new_org"  # Updated
        assert update_call_args["notes"] == "patched description"  # Updated
