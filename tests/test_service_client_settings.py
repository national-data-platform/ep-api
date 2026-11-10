"""The Endpoint reads its service client from the environment (issue #412)."""

from api.config.swagger_settings import Settings


def test_the_service_client_is_read_from_the_environment(monkeypatch):
    monkeypatch.setenv("OIDC_SERVICE_CLIENT_ID", "ep-0123")
    monkeypatch.setenv("OIDC_SERVICE_CLIENT_SECRET", "a-secret")

    settings = Settings()

    assert settings.oidc_service_client_id == "ep-0123"
    assert settings.oidc_service_client_secret.get_secret_value() == "a-secret"


def test_the_secret_does_not_show_in_the_settings_text(monkeypatch):
    monkeypatch.setenv("OIDC_SERVICE_CLIENT_SECRET", "a-secret")

    settings = Settings()

    assert "a-secret" not in repr(settings)
    assert "a-secret" not in str(settings.model_dump())


def test_unset_means_no_service_client(monkeypatch):
    monkeypatch.delenv("OIDC_SERVICE_CLIENT_ID", raising=False)
    monkeypatch.delenv("OIDC_SERVICE_CLIENT_SECRET", raising=False)

    settings = Settings(_env_file=None)

    assert settings.oidc_service_client_id == ""
    assert settings.oidc_service_client_secret.get_secret_value() == ""
