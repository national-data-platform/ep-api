# tests/test_stream_kafka_models.py
"""
Tests for stream and Kafka response models.

Tests for request_stream_model.py and response_kafka_model.py
"""

import pytest
from pydantic import ValidationError

from api.models.request_stream_model import ProducerPayload
from api.models.response_kafka_model import KafkaResource, KafkaDataSourceResponse


class TestProducerPayload:
    """Tests for ProducerPayload model."""

    def test_create_with_all_fields(self):
        """Test creating ProducerPayload with all fields."""
        payload = ProducerPayload(
            keywords="temperature,humidity",
            match_all=True,
            filter_semantics=["temp>10", "humidity<50"],
        )

        assert payload.keywords == "temperature,humidity"
        assert payload.match_all is True
        assert payload.filter_semantics == ["temp>10", "humidity<50"]

    def test_create_with_defaults(self):
        """Test creating ProducerPayload with default values."""
        payload = ProducerPayload()

        assert payload.keywords is None
        assert payload.match_all is False
        assert payload.filter_semantics == []

    def test_create_with_partial_fields(self):
        """Test creating ProducerPayload with some fields."""
        payload = ProducerPayload(keywords="temperature")

        assert payload.keywords == "temperature"
        assert payload.match_all is False
        assert payload.filter_semantics == []

    def test_match_all_false_by_default(self):
        """Test that match_all defaults to False."""
        payload = ProducerPayload(keywords="test")

        assert payload.match_all is False

    def test_filter_semantics_empty_by_default(self):
        """Test that filter_semantics defaults to empty list."""
        payload = ProducerPayload()

        assert payload.filter_semantics == []


class TestKafkaResource:
    """Tests for KafkaResource model."""

    def test_create_with_required_fields(self):
        """Test creating KafkaResource with all required fields."""
        resource = KafkaResource(
            id="resource-123",
            kafka_host="localhost",
            kafka_port="9092",
            kafka_topic="test-topic",
        )

        assert resource.id == "resource-123"
        assert resource.kafka_host == "localhost"
        assert resource.kafka_port == "9092"
        assert resource.kafka_topic == "test-topic"
        assert resource.description is None

    def test_create_with_description(self):
        """Test creating KafkaResource with description."""
        resource = KafkaResource(
            id="resource-456",
            kafka_host="kafka.example.com",
            kafka_port="9093",
            kafka_topic="events",
            description="Event stream",
        )

        assert resource.description == "Event stream"

    def test_missing_required_field_raises_error(self):
        """Test that missing required fields raise ValidationError."""
        with pytest.raises(ValidationError):
            KafkaResource(
                kafka_host="localhost",
                kafka_port="9092",
                # Missing id and kafka_topic
            )


class TestKafkaDataSourceResponse:
    """Tests for KafkaDataSourceResponse model."""

    def test_create_with_required_fields(self):
        """Test creating KafkaDataSourceResponse with required fields."""
        resource = KafkaResource(
            id="res-1", kafka_host="localhost", kafka_port="9092", kafka_topic="topic1"
        )

        response = KafkaDataSourceResponse(
            id="dataset-123",
            name="my-kafka-dataset",
            title="My Kafka Dataset",
            resources=[resource],
        )

        assert response.id == "dataset-123"
        assert response.name == "my-kafka-dataset"
        assert response.title == "My Kafka Dataset"
        assert len(response.resources) == 1
        assert response.organization_id is None
        assert response.description is None
        assert response.extras is None

    def test_create_with_all_fields(self):
        """Test creating KafkaDataSourceResponse with all fields."""
        resource = KafkaResource(
            id="res-1",
            kafka_host="localhost",
            kafka_port="9092",
            kafka_topic="topic1",
            description="Test resource",
        )

        response = KafkaDataSourceResponse(
            id="dataset-456",
            name="full-dataset",
            title="Full Dataset",
            organization_id="org-789",
            description="Full description",
            resources=[resource],
            extras={"key1": "value1", "key2": "value2"},
        )

        assert response.id == "dataset-456"
        assert response.organization_id == "org-789"
        assert response.description == "Full description"
        assert response.extras == {"key1": "value1", "key2": "value2"}

    def test_create_with_multiple_resources(self):
        """Test creating KafkaDataSourceResponse with multiple resources."""
        resources = [
            KafkaResource(
                id=f"res-{i}",
                kafka_host="localhost",
                kafka_port="9092",
                kafka_topic=f"topic-{i}",
            )
            for i in range(3)
        ]

        response = KafkaDataSourceResponse(
            id="dataset-multi",
            name="multi-resource",
            title="Multi Resource Dataset",
            resources=resources,
        )

        assert len(response.resources) == 3
        assert response.resources[0].id == "res-0"
        assert response.resources[2].kafka_topic == "topic-2"

    def test_populate_by_name_with_aliases(self):
        """Test that aliases work correctly (owner_org, notes)."""
        resource = KafkaResource(
            id="res-1", kafka_host="localhost", kafka_port="9092", kafka_topic="topic1"
        )

        # Using aliases
        response = KafkaDataSourceResponse(
            id="dataset-alias",
            name="alias-test",
            title="Alias Test",
            owner_org="org-123",  # Using alias
            notes="Test notes",  # Using alias
            resources=[resource],
        )

        assert response.organization_id == "org-123"
        assert response.description == "Test notes"

    def test_missing_required_field_raises_error(self):
        """Test that missing required fields raise ValidationError."""
        resource = KafkaResource(
            id="res-1", kafka_host="localhost", kafka_port="9092", kafka_topic="topic1"
        )

        with pytest.raises(ValidationError):
            KafkaDataSourceResponse(
                id="dataset-incomplete",
                name="incomplete",
                # Missing title and resources
            )
