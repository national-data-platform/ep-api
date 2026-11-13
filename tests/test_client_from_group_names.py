"""
An Endpoint installed before OIDC_SERVICE_CLIENT_ID existed (0.34.79) has
only GROUP_NAMES (``ndp_ep/ep-<config-id>``) in its .env. Upgrading it must
not leave every
gate without a client, which refused every request; the client is taken from
that group instead.
"""

import pytest

from api.config.swagger_settings import Settings, client_id_from_group_names


@pytest.mark.parametrize(
    "group_names, client",
    [
        ("ndp_ep/ep-6a5e300b7770ef7b55e0ce6b", "ep-6a5e300b7770ef7b55e0ce6b"),
        ("/ndp_ep/ep-abc123", "ep-abc123"),
        ("other-group, ndp_ep/ep-abc123", "ep-abc123"),
        ("ndp_ep/ep-first,ndp_ep/ep-second", "ep-first"),
        ("", ""),
        ("some-org,another", ""),
        ("ndp_ep/ep-abc/admins", ""),
    ],
)
def test_client_from_group_names(group_names, client):
    assert client_id_from_group_names(group_names) == client


def test_an_upgraded_endpoint_gets_its_client(monkeypatch):
    monkeypatch.delenv("OIDC_SERVICE_CLIENT_ID", raising=False)
    monkeypatch.setenv("GROUP_NAMES", "ndp_ep/ep-abc123")

    assert Settings(_env_file=None).oidc_service_client_id == "ep-abc123"


def test_an_explicit_client_wins(monkeypatch):
    monkeypatch.setenv("OIDC_SERVICE_CLIENT_ID", "ep-explicit")
    monkeypatch.setenv("GROUP_NAMES", "ndp_ep/ep-abc123")

    assert Settings(_env_file=None).oidc_service_client_id == "ep-explicit"


def test_nothing_set_stays_unset(monkeypatch):
    monkeypatch.delenv("OIDC_SERVICE_CLIENT_ID", raising=False)
    monkeypatch.delenv("GROUP_NAMES", raising=False)

    assert Settings(_env_file=None).oidc_service_client_id == ""
