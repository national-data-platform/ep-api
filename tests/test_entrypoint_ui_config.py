# tests/test_entrypoint_ui_config.py
"""
The UI's runtime config, config.js, that entrypoint.sh writes at container
start. It is served to anyone, signed in or not, so while sign-in is off it
carries no client, realm or callback address, and the service client's
secret never appears in it. These tests run the part of entrypoint.sh that
writes it, with config.js redirected to a temporary file.
"""

import re
import subprocess
from pathlib import Path

import pytest

ENTRYPOINT = Path(__file__).resolve().parents[1] / "entrypoint.sh"
CONFIG_JS = "/app/ui/build/config.js"

SERVICE_CLIENT = {
    "OIDC_SERVICE_CLIENT_ID": "ep-0123",
    "OIDC_SERVICE_CLIENT_SECRET": "s3cret",
    "OIDC_REDIRECT_URI": "https://ep.example.org/ui/auth/callback",
    "KEYCLOAK_URL": "https://idp.example.org",
    "AUTHZ_REALM": "NDP",
}


def _config(tmp_path, env):
    """Run the config.js part of entrypoint.sh; return its text and values."""
    text = ENTRYPOINT.read_text(encoding="utf-8")
    end = text.index("\nEOF\n", text.index(CONFIG_JS)) + len("\nEOF\n")
    out = tmp_path / "config.js"
    subprocess.run(
        ["sh", "-c", text[:end].replace(CONFIG_JS, str(out))],
        env={"PATH": "/usr/bin:/bin", **env},
        check=True,
    )
    written = out.read_text(encoding="utf-8")
    return written, dict(re.findall(r'^\s*(\w+): "(.*)",?$', written, re.M))


@pytest.mark.parametrize("enabled", [None, "", "False", "false", "0", "no"])
def test_off_publishes_no_client_realm_or_callback(tmp_path, enabled):
    env = dict(SERVICE_CLIENT)
    if enabled is not None:
        env["OIDC_ENABLED"] = enabled

    written, config = _config(tmp_path, env)

    assert config["oidcEnabled"] == "False"
    assert config["oidcClientId"] == ""
    assert config["oidcIssuer"] == ""
    assert config["oidcRedirectUri"] == ""
    assert "ep-0123" not in written
    assert "s3cret" not in written


@pytest.mark.parametrize("enabled", ["True", "true", "1", "yes", "ON"])
def test_on_signs_in_with_the_service_client(tmp_path, enabled):
    written, config = _config(tmp_path, {**SERVICE_CLIENT, "OIDC_ENABLED": enabled})

    assert config["oidcEnabled"] == "True"
    assert config["oidcClientId"] == "ep-0123"
    assert config["oidcIssuer"] == "https://idp.example.org/realms/NDP"
    assert config["oidcRedirectUri"] == "https://ep.example.org/ui/auth/callback"
    assert "s3cret" not in written


def test_the_old_public_client_settings_are_ignored(tmp_path):
    """OIDC_CLIENT_ID and OIDC_ISSUER named a public client, a mode removed:
    an .env that still has them signs in with the service client."""
    env = {**SERVICE_CLIENT, "OIDC_ENABLED": "True"}
    env["OIDC_CLIENT_ID"] = "a-public-client"
    env["OIDC_ISSUER"] = "https://other.example.org/realms/X"

    written, config = _config(tmp_path, env)

    assert config["oidcClientId"] == "ep-0123"
    assert config["oidcIssuer"] == "https://idp.example.org/realms/NDP"
    assert "a-public-client" not in written
    assert "other.example.org" not in written


def test_the_old_auth_api_url_gives_the_host(tmp_path):
    env = {**SERVICE_CLIENT, "OIDC_ENABLED": "True"}
    del env["KEYCLOAK_URL"]
    env["AUTH_API_URL"] = "https://idp-test.example.org/temp/information"

    _, config = _config(tmp_path, env)

    assert config["oidcIssuer"] == "https://idp-test.example.org/realms/NDP"


def test_without_the_secret_nothing_is_published(tmp_path):
    env = {**SERVICE_CLIENT, "OIDC_ENABLED": "True"}
    del env["OIDC_SERVICE_CLIENT_SECRET"]

    written, config = _config(tmp_path, env)

    assert config["oidcClientId"] == ""
    assert config["oidcIssuer"] == ""
    assert config["oidcRedirectUri"] == ""
    assert "ep-0123" not in written
