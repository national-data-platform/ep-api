# api/config/kafka_settings.py

from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import Optional


class KafkaSettings(BaseSettings):
    kafka_connection: bool = False
    kafka_host: str = "localhost"
    kafka_port: int = 9092
    kafka_prefix: str = "data_stream_"
    max_streams: int = 10

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
