class TestConfigValidation:
    """Test configuration validation."""

    def test_ckan_settings_validation(self):
        """Test CKAN settings validation."""
        from api.config.ckan_settings import ckan_settings

        # Test that settings object exists and has expected attributes
        assert hasattr(ckan_settings, "ckan_local_enabled")
        assert hasattr(ckan_settings, "ckan_url")
        assert hasattr(ckan_settings, "ckan_api_key")
        assert hasattr(ckan_settings, "pre_ckan_enabled")

    def test_kafka_settings_validation(self):
        """Test Kafka settings validation."""
        from api.config.kafka_settings import kafka_settings

        # Test that settings object exists and has expected attributes
        assert hasattr(kafka_settings, "kafka_connection")
        assert hasattr(kafka_settings, "kafka_host")
        assert hasattr(kafka_settings, "kafka_port")

    def test_main_app_creation(self):
        """Test that FastAPI app is created correctly."""
        from api.main import app

        assert app is not None
        assert app.title is not None
        assert app.version is not None


class TestModelValidation:
    """Test model validation edge cases."""

    def test_token_model_validation(self):
        """Test token model validation."""
        from api.models.token_model import Token

        # Test valid token
        token = Token(access_token="test_token", token_type="bearer")
        assert token.access_token == "test_token"
        assert token.token_type == "bearer"
