"""
The Kafka readiness check can run (issue #317).

``_check_kafka`` imports ``kafka-python``, which was not a dependency, so with
KAFKA_CONNECTION=True the import failed and /ready reported Kafka down — and the
Endpoint unhealthy — even with the broker up.
"""

from unittest.mock import MagicMock, patch

import pytest
from kafka.errors import KafkaError

from api.routes.health_routes import ready


def test_the_kafka_client_is_installed():
    from kafka import KafkaProducer  # noqa: F401 - the import is the test


def test_a_reachable_broker_is_up():
    with (
        patch.object(ready.kafka_settings, "kafka_connection", True),
        patch("kafka.KafkaProducer", return_value=MagicMock()) as producer,
    ):
        result = ready._check_kafka()

    assert result["status"] == "up"
    producer.return_value.close.assert_called_once()


@pytest.mark.parametrize(
    "error",
    # kafka-python raises KafkaError subclasses, and in 3.x a ValueError when
    # no broker answers at all; both must read as down, not crash the probe.
    [KafkaError("no broker"), ValueError("no broker")],
)
def test_an_unreachable_broker_is_down(error):
    with (
        patch.object(ready.kafka_settings, "kafka_connection", True),
        patch("kafka.KafkaProducer", side_effect=error),
    ):
        result = ready._check_kafka()

    assert result["status"] == "down"


def test_every_option_passed_to_the_producer_exists():
    """kafka-python 3 rejects unknown options; a renamed one made /ready fail."""
    from kafka import KafkaProducer

    with (
        patch.object(ready.kafka_settings, "kafka_connection", True),
        patch("kafka.KafkaProducer", return_value=MagicMock()) as producer,
    ):
        ready._check_kafka()

    unknown = set(producer.call_args.kwargs) - set(KafkaProducer.DEFAULT_CONFIG)
    assert not unknown
