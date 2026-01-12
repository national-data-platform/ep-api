# tests/test_kafka_services.py
"""Tests for Kafka services (add_kafka, update_kafka, patch_kafka)."""

import pytest
from unittest.mock import MagicMock, patch

from api.services.kafka_services.add_kafka import add_kafka, RESERVED_KEYS
from api.services.kafka_services.update_kafka import update_kafka, patch_kafka


class TestAddKafka:
    """Tests for add_kafka service."""

    @patch("api.services.kafka_services.add_kafka.catalog_settings")
    def test_add_kafka_success(self, mock_catalog_settings):
        """Test successful Kafka dataset creation."""
        mock_repo = MagicMock()
        mock_repo.package_create.return_value = {"id": "dataset-123"}
        mock_repo.resource_create.return_value = {"id": "resource-456"}
        mock_catalog_settings.local_catalog = mock_repo

        result = add_kafka(
            dataset_name="test-kafka",
            dataset_title="Test Kafka Dataset",
            owner_org="test-org",
            kafka_topic="my-topic",
            kafka_host="kafka.example.com",
            kafka_port="9092",
        )

        assert result == "dataset-123"
        mock_repo.package_create.assert_called_once()
        mock_repo.resource_create.assert_called_once()

    @patch("api.services.kafka_services.add_kafka.catalog_settings")
    def test_add_kafka_with_description(self, mock_catalog_settings):
        """Test Kafka dataset creation with description."""
        mock_repo = MagicMock()
        mock_repo.package_create.return_value = {"id": "dataset-123"}
        mock_repo.resource_create.return_value = {"id": "resource-456"}
        mock_catalog_settings.local_catalog = mock_repo

        result = add_kafka(
            dataset_name="test-kafka",
            dataset_title="Test Kafka Dataset",
            owner_org="test-org",
            kafka_topic="my-topic",
            kafka_host="kafka.example.com",
            kafka_port=9092,
            dataset_description="A test Kafka dataset",
        )

        assert result == "dataset-123"
        call_args = mock_repo.package_create.call_args
        assert call_args[1]["notes"] == "A test Kafka dataset"

    @patch("api.services.kafka_services.add_kafka.catalog_settings")
    def test_add_kafka_with_extras(self, mock_catalog_settings):
        """Test Kafka dataset creation with extra metadata."""
        mock_repo = MagicMock()
        mock_repo.package_create.return_value = {"id": "dataset-123"}
        mock_repo.resource_create.return_value = {"id": "resource-456"}
        mock_catalog_settings.local_catalog = mock_repo

        result = add_kafka(
            dataset_name="test-kafka",
            dataset_title="Test Kafka Dataset",
            owner_org="test-org",
            kafka_topic="my-topic",
            kafka_host="kafka.example.com",
            kafka_port="9092",
            extras={"custom_field": "custom_value"},
        )

        assert result == "dataset-123"

    @patch("api.services.kafka_services.add_kafka.catalog_settings")
    def test_add_kafka_with_mapping_and_processing(self, mock_catalog_settings):
        """Test Kafka dataset creation with mapping and processing."""
        mock_repo = MagicMock()
        mock_repo.package_create.return_value = {"id": "dataset-123"}
        mock_repo.resource_create.return_value = {"id": "resource-456"}
        mock_catalog_settings.local_catalog = mock_repo

        result = add_kafka(
            dataset_name="test-kafka",
            dataset_title="Test Kafka Dataset",
            owner_org="test-org",
            kafka_topic="my-topic",
            kafka_host="kafka.example.com",
            kafka_port="9092",
            mapping={"field1": "value1"},
            processing={"step1": "transform"},
        )

        assert result == "dataset-123"

    def test_add_kafka_invalid_port(self):
        """Test error when kafka_port is invalid."""
        with pytest.raises(ValueError) as exc_info:
            add_kafka(
                dataset_name="test-kafka",
                dataset_title="Test Kafka Dataset",
                owner_org="test-org",
                kafka_topic="my-topic",
                kafka_host="kafka.example.com",
                kafka_port="invalid",
            )

        assert "kafka_port must be an integer" in str(exc_info.value)

    def test_add_kafka_invalid_extras_type(self):
        """Test error when extras is not a dict."""
        with pytest.raises(ValueError) as exc_info:
            add_kafka(
                dataset_name="test-kafka",
                dataset_title="Test Kafka Dataset",
                owner_org="test-org",
                kafka_topic="my-topic",
                kafka_host="kafka.example.com",
                kafka_port="9092",
                extras="not-a-dict",
            )

        assert "Extras must be a dictionary" in str(exc_info.value)

    def test_add_kafka_reserved_keys_in_extras(self):
        """Test error when extras contains reserved keys."""
        with pytest.raises(KeyError) as exc_info:
            add_kafka(
                dataset_name="test-kafka",
                dataset_title="Test Kafka Dataset",
                owner_org="test-org",
                kafka_topic="my-topic",
                kafka_host="kafka.example.com",
                kafka_port="9092",
                extras={"name": "reserved"},
            )

        assert "reserved keys" in str(exc_info.value)

    @patch("api.services.kafka_services.add_kafka.catalog_settings")
    def test_add_kafka_dataset_creation_error(self, mock_catalog_settings):
        """Test error during dataset creation."""
        mock_repo = MagicMock()
        mock_repo.package_create.side_effect = Exception("CKAN error")
        mock_catalog_settings.local_catalog = mock_repo

        with pytest.raises(Exception) as exc_info:
            add_kafka(
                dataset_name="test-kafka",
                dataset_title="Test Kafka Dataset",
                owner_org="test-org",
                kafka_topic="my-topic",
                kafka_host="kafka.example.com",
                kafka_port="9092",
            )

        assert "Error creating Kafka dataset" in str(exc_info.value)

    @patch("api.services.kafka_services.add_kafka.catalog_settings")
    def test_add_kafka_resource_creation_error(self, mock_catalog_settings):
        """Test error during resource creation."""
        mock_repo = MagicMock()
        mock_repo.package_create.return_value = {"id": "dataset-123"}
        mock_repo.resource_create.side_effect = Exception("Resource error")
        mock_catalog_settings.local_catalog = mock_repo

        with pytest.raises(Exception) as exc_info:
            add_kafka(
                dataset_name="test-kafka",
                dataset_title="Test Kafka Dataset",
                owner_org="test-org",
                kafka_topic="my-topic",
                kafka_host="kafka.example.com",
                kafka_port="9092",
            )

        assert "Error creating Kafka resource" in str(exc_info.value)

    @patch("api.services.kafka_services.add_kafka.CKANRepository")
    def test_add_kafka_with_custom_ckan_instance(self, mock_ckan_repo_class):
        """Test Kafka dataset creation with custom CKAN instance."""
        mock_repo = MagicMock()
        mock_repo.package_create.return_value = {"id": "dataset-123"}
        mock_repo.resource_create.return_value = {"id": "resource-456"}
        mock_ckan_repo_class.return_value = mock_repo

        mock_ckan_instance = MagicMock()

        result = add_kafka(
            dataset_name="test-kafka",
            dataset_title="Test Kafka Dataset",
            owner_org="test-org",
            kafka_topic="my-topic",
            kafka_host="kafka.example.com",
            kafka_port="9092",
            ckan_instance=mock_ckan_instance,
        )

        assert result == "dataset-123"
        mock_ckan_repo_class.assert_called_once_with(mock_ckan_instance)

    @patch("api.services.kafka_services.add_kafka.catalog_settings")
    @patch("api.services.kafka_services.add_kafka.inject_ndp_metadata")
    def test_add_kafka_with_user_info(self, mock_inject, mock_catalog_settings):
        """Test Kafka dataset creation with user info for metadata injection."""
        mock_repo = MagicMock()
        mock_repo.package_create.return_value = {"id": "dataset-123"}
        mock_repo.resource_create.return_value = {"id": "resource-456"}
        mock_catalog_settings.local_catalog = mock_repo
        mock_inject.return_value = {
            "host": "kafka.example.com",
            "port": 9092,
            "topic": "my-topic",
            "user": "test",
        }

        result = add_kafka(
            dataset_name="test-kafka",
            dataset_title="Test Kafka Dataset",
            owner_org="test-org",
            kafka_topic="my-topic",
            kafka_host="kafka.example.com",
            kafka_port="9092",
            user_info={"username": "test-user"},
        )

        assert result == "dataset-123"
        mock_inject.assert_called_once()


class TestUpdateKafka:
    """Tests for update_kafka service."""

    @patch("api.services.kafka_services.update_kafka.ckan_settings")
    def test_update_kafka_success(self, mock_ckan_settings):
        """Test successful Kafka dataset update."""
        mock_ckan = MagicMock()
        mock_ckan.action.package_show.return_value = {
            "id": "dataset-123",
            "name": "old-name",
            "title": "Old Title",
            "owner_org": "old-org",
            "notes": "Old description",
            "extras": [],
        }
        mock_ckan.action.package_update.return_value = {"id": "dataset-123"}
        mock_ckan_settings.ckan = mock_ckan

        result = update_kafka(
            dataset_id="dataset-123",
            dataset_name="new-name",
            dataset_title="New Title",
        )

        assert result == "dataset-123"
        mock_ckan.action.package_update.assert_called_once()

    @patch("api.services.kafka_services.update_kafka.ckan_settings")
    def test_update_kafka_with_kafka_fields(self, mock_ckan_settings):
        """Test updating Kafka-specific fields."""
        mock_ckan = MagicMock()
        mock_ckan.action.package_show.return_value = {
            "id": "dataset-123",
            "name": "test",
            "title": "Test",
            "extras": [{"key": "host", "value": "old-host"}],
        }
        mock_ckan.action.package_update.return_value = {"id": "dataset-123"}
        mock_ckan_settings.ckan = mock_ckan

        result = update_kafka(
            dataset_id="dataset-123",
            kafka_host="new-host",
            kafka_port="9093",
            kafka_topic="new-topic",
        )

        assert result == "dataset-123"

    @patch("api.services.kafka_services.update_kafka.ckan_settings")
    def test_update_kafka_with_mapping(self, mock_ckan_settings):
        """Test updating with mapping."""
        mock_ckan = MagicMock()
        mock_ckan.action.package_show.return_value = {
            "id": "dataset-123",
            "extras": [],
        }
        mock_ckan.action.package_update.return_value = {"id": "dataset-123"}
        mock_ckan_settings.ckan = mock_ckan

        result = update_kafka(
            dataset_id="dataset-123",
            mapping={"field": "value"},
        )

        assert result == "dataset-123"

    @patch("api.services.kafka_services.update_kafka.ckan_settings")
    def test_update_kafka_with_processing(self, mock_ckan_settings):
        """Test updating with processing."""
        mock_ckan = MagicMock()
        mock_ckan.action.package_show.return_value = {
            "id": "dataset-123",
            "extras": [],
        }
        mock_ckan.action.package_update.return_value = {"id": "dataset-123"}
        mock_ckan_settings.ckan = mock_ckan

        result = update_kafka(
            dataset_id="dataset-123",
            processing={"step": "process"},
        )

        assert result == "dataset-123"

    @patch("api.services.kafka_services.update_kafka.ckan_settings")
    def test_update_kafka_reserved_keys_error(self, mock_ckan_settings):
        """Test error when extras contains reserved keys."""
        mock_ckan = MagicMock()
        mock_ckan.action.package_show.return_value = {
            "id": "dataset-123",
            "extras": [],
        }
        mock_ckan_settings.ckan = mock_ckan

        with pytest.raises(KeyError) as exc_info:
            update_kafka(
                dataset_id="dataset-123",
                extras={"name": "reserved"},
            )

        assert "reserved keys" in str(exc_info.value)

    @patch("api.services.kafka_services.update_kafka.ckan_settings")
    def test_update_kafka_fetch_error(self, mock_ckan_settings):
        """Test error when fetching dataset fails."""
        mock_ckan = MagicMock()
        mock_ckan.action.package_show.side_effect = Exception("Not found")
        mock_ckan_settings.ckan = mock_ckan

        with pytest.raises(Exception) as exc_info:
            update_kafka(dataset_id="nonexistent")

        assert "Error fetching Kafka dataset" in str(exc_info.value)

    @patch("api.services.kafka_services.update_kafka.ckan_settings")
    def test_update_kafka_update_error(self, mock_ckan_settings):
        """Test error when updating dataset fails."""
        mock_ckan = MagicMock()
        mock_ckan.action.package_show.return_value = {
            "id": "dataset-123",
            "extras": [],
        }
        mock_ckan.action.package_update.side_effect = Exception("Update failed")
        mock_ckan_settings.ckan = mock_ckan

        with pytest.raises(Exception) as exc_info:
            update_kafka(dataset_id="dataset-123")

        assert "Error updating Kafka dataset" in str(exc_info.value)

    def test_update_kafka_with_custom_instance(self):
        """Test update with custom CKAN instance."""
        mock_ckan = MagicMock()
        mock_ckan.action.package_show.return_value = {
            "id": "dataset-123",
            "extras": [],
        }
        mock_ckan.action.package_update.return_value = {"id": "dataset-123"}

        result = update_kafka(
            dataset_id="dataset-123",
            ckan_instance=mock_ckan,
        )

        assert result == "dataset-123"


class TestPatchKafka:
    """Tests for patch_kafka service."""

    @patch("api.services.kafka_services.update_kafka.ckan_settings")
    def test_patch_kafka_success(self, mock_ckan_settings):
        """Test successful Kafka dataset patch."""
        mock_ckan = MagicMock()
        mock_ckan.action.package_show.return_value = {
            "id": "dataset-123",
            "name": "old-name",
            "title": "Old Title",
            "extras": [],
        }
        mock_ckan.action.package_update.return_value = {"id": "dataset-123"}
        mock_ckan_settings.ckan = mock_ckan

        result = patch_kafka(
            dataset_id="dataset-123",
            dataset_title="New Title",
        )

        assert result == "dataset-123"

    @patch("api.services.kafka_services.update_kafka.ckan_settings")
    def test_patch_kafka_partial_update(self, mock_ckan_settings):
        """Test patching only specific fields."""
        mock_ckan = MagicMock()
        mock_ckan.action.package_show.return_value = {
            "id": "dataset-123",
            "name": "original-name",
            "title": "Original Title",
            "owner_org": "original-org",
            "notes": "Original notes",
            "extras": [{"key": "host", "value": "original-host"}],
        }
        mock_ckan.action.package_update.return_value = {"id": "dataset-123"}
        mock_ckan_settings.ckan = mock_ckan

        result = patch_kafka(
            dataset_id="dataset-123",
            kafka_host="new-host",
        )

        assert result == "dataset-123"

    @patch("api.services.kafka_services.update_kafka.ckan_settings")
    def test_patch_kafka_with_mapping(self, mock_ckan_settings):
        """Test patching with mapping."""
        mock_ckan = MagicMock()
        mock_ckan.action.package_show.return_value = {
            "id": "dataset-123",
            "extras": [],
        }
        mock_ckan.action.package_update.return_value = {"id": "dataset-123"}
        mock_ckan_settings.ckan = mock_ckan

        result = patch_kafka(
            dataset_id="dataset-123",
            mapping={"new": "mapping"},
        )

        assert result == "dataset-123"

    @patch("api.services.kafka_services.update_kafka.ckan_settings")
    def test_patch_kafka_with_processing(self, mock_ckan_settings):
        """Test patching with processing."""
        mock_ckan = MagicMock()
        mock_ckan.action.package_show.return_value = {
            "id": "dataset-123",
            "extras": [],
        }
        mock_ckan.action.package_update.return_value = {"id": "dataset-123"}
        mock_ckan_settings.ckan = mock_ckan

        result = patch_kafka(
            dataset_id="dataset-123",
            processing={"new": "processing"},
        )

        assert result == "dataset-123"

    @patch("api.services.kafka_services.update_kafka.ckan_settings")
    def test_patch_kafka_reserved_keys_error(self, mock_ckan_settings):
        """Test error when extras contains reserved keys."""
        mock_ckan = MagicMock()
        mock_ckan.action.package_show.return_value = {
            "id": "dataset-123",
            "extras": [],
        }
        mock_ckan_settings.ckan = mock_ckan

        with pytest.raises(KeyError) as exc_info:
            patch_kafka(
                dataset_id="dataset-123",
                extras={"topic": "reserved"},
            )

        assert "reserved keys" in str(exc_info.value)

    @patch("api.services.kafka_services.update_kafka.ckan_settings")
    def test_patch_kafka_fetch_error(self, mock_ckan_settings):
        """Test error when fetching dataset fails."""
        mock_ckan = MagicMock()
        mock_ckan.action.package_show.side_effect = Exception("Not found")
        mock_ckan_settings.ckan = mock_ckan

        with pytest.raises(Exception) as exc_info:
            patch_kafka(dataset_id="nonexistent")

        assert "Error fetching Kafka dataset" in str(exc_info.value)

    @patch("api.services.kafka_services.update_kafka.ckan_settings")
    def test_patch_kafka_update_error(self, mock_ckan_settings):
        """Test error when updating dataset fails."""
        mock_ckan = MagicMock()
        mock_ckan.action.package_show.return_value = {
            "id": "dataset-123",
            "extras": [],
        }
        mock_ckan.action.package_update.side_effect = Exception("Update failed")
        mock_ckan_settings.ckan = mock_ckan

        with pytest.raises(Exception) as exc_info:
            patch_kafka(dataset_id="dataset-123")

        assert "Error updating Kafka dataset" in str(exc_info.value)

    def test_patch_kafka_with_custom_instance(self):
        """Test patch with custom CKAN instance."""
        mock_ckan = MagicMock()
        mock_ckan.action.package_show.return_value = {
            "id": "dataset-123",
            "extras": [],
        }
        mock_ckan.action.package_update.return_value = {"id": "dataset-123"}

        result = patch_kafka(
            dataset_id="dataset-123",
            ckan_instance=mock_ckan,
        )

        assert result == "dataset-123"

    @patch("api.services.kafka_services.update_kafka.ckan_settings")
    def test_patch_kafka_with_extras(self, mock_ckan_settings):
        """Test patching with custom extras."""
        mock_ckan = MagicMock()
        mock_ckan.action.package_show.return_value = {
            "id": "dataset-123",
            "extras": [{"key": "existing", "value": "value"}],
        }
        mock_ckan.action.package_update.return_value = {"id": "dataset-123"}
        mock_ckan_settings.ckan = mock_ckan

        result = patch_kafka(
            dataset_id="dataset-123",
            extras={"custom": "extra"},
        )

        assert result == "dataset-123"
