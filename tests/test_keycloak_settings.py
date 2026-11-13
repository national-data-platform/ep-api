# tests/test_keycloak_settings.py
"""
KEYCLOAK_URL is the identity provider's host; the AAI API and the realm are
derived from it. AUTH_API_URL, the old name, still works: only its host is
kept.
"""

import pytest

from api.config.swagger_settings import Settings


@pytest.fixture(autouse=True)
def _no_identity_env(monkeypatch):
    for name in ("KEYCLOAK_URL", "AUTH_API_URL", "AUTHZ_REALM"):
        monkeypatch.delenv(name, raising=False)


def test_both_urls_are_derived_from_the_host(monkeypatch):
    monkeypatch.setenv("KEYCLOAK_URL", "https://idp-test.example.org")
    monkeypatch.setenv("AUTHZ_REALM", "Other")

    settings = Settings(_env_file=None)

    assert settings.aai_api_url == "https://idp-test.example.org/api"
    assert settings.keycloak_realm_url == "https://idp-test.example.org/realms/Other"


def test_the_default_is_the_national_data_platform():
    settings = Settings(_env_file=None)

    assert settings.keycloak_url == "https://idp.nationaldataplatform.org"
    assert settings.keycloak_realm_url == (
        "https://idp.nationaldataplatform.org/realms/NDP"
    )


def test_the_old_auth_api_url_still_names_the_host(monkeypatch):
    monkeypatch.setenv("AUTH_API_URL", "https://idp-test.example.org/temp/information")

    assert Settings(_env_file=None).keycloak_url == "https://idp-test.example.org"


def test_keycloak_url_wins_over_the_old_name(monkeypatch):
    monkeypatch.setenv("KEYCLOAK_URL", "https://new.example.org/")
    monkeypatch.setenv("AUTH_API_URL", "https://old.example.org/temp/information")

    assert Settings(_env_file=None).keycloak_url == "https://new.example.org"
