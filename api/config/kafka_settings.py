# api/config/kafka_settings.py

from pydantic_settings import BaseSettings
from pydantic import field_validator


class KafkaSettings(BaseSettings):
    kafka_connection: bool = False
    kafka_host: str = "localhost"
    kafka_port: int = 9092
    kafka_prefix: str = "data_stream_"
    # NDP-EP is the sole owner of this quota. None means unlimited.
    max_streams: int | None = 10

    @field_validator("kafka_port", mode="before")
    @classmethod
    def validate_kafka_port(cls, v):
        """Handle empty string or None when Kafka is disabled."""
        if v is None or v == "":
            return 9092  # Return default value
        return int(v)

    @field_validator("kafka_host", mode="before")
    @classmethod
    def validate_kafka_host(cls, v):
        """Handle empty string or None when Kafka is disabled."""
        if v is None or v == "":
            return "localhost"  # Return default value
        return v

    @field_validator("max_streams", mode="before")
    @classmethod
    def validate_max_streams(cls, v):
        """Treat a blank MAX_STREAMS as an unlimited quota."""
        if v is None or v == "":
            return None
        if isinstance(v, bool) or isinstance(v, float):
            raise ValueError("MAX_STREAMS must be a non-negative integer or blank.")
        try:
            value = int(v)
        except (TypeError, ValueError) as exc:
            raise ValueError(
                "MAX_STREAMS must be a non-negative integer or blank."
            ) from exc
        if value < 0:
            raise ValueError("MAX_STREAMS must be a non-negative integer or blank.")
        return value

    @property
    def connection_details(self):
        return {
            "kafka_connection": self.kafka_connection,
            "kafka_host": self.kafka_host,
            "kafka_port": self.kafka_port,
            "kafka_prefix": self.kafka_prefix,
            "max_streams": self.max_streams,
        }

    model_config = {
        "env_file": ".env",
        "extra": "allow",
    }


kafka_settings = KafkaSettings()
