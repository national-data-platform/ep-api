"""
The installer joins NDP's NetBird network and turns Affinities on (issue #359).

Both are opt-in (``--netbird``, ``--affinities``) and remembered, so a re-run
keeps them. The URLs come from the Federation configuration
(sci-ndp/ndp-federation#122), not from the installer. The NetBird setup key is
read from a file or a hidden prompt and never written anywhere.

A stand-in Federation serves the configuration; ``netbird`` and ``sudo`` are
stubs, so nothing is installed and no network is joined.
"""

import json
import os
import re
import shutil
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
BASH = shutil.which("bash")

pytestmark = pytest.mark.skipif(
    BASH is None or os.name == "nt" or shutil.which("curl") is None,
    reason="needs bash and curl",
)

CONFIG_ID = "cfg359"
SETUP_KEY = "SETUP-KEY-359-never-stored"
MANAGEMENT_URL = "https://netbird.example.org"
FEDERATION_KEY = "KEY-FROM-THE-FEDERATION-361"
OWNER_TOKEN = "owner-ndp-token-361"


def _configuration(**extra):
    return {
        "_id": CONFIG_ID,
        "organization": "ORG-359",
        "ep_name": "EP-359",
        "group_name": "ndp_ep/ep-cfg359",
        **extra,
    }


@pytest.fixture
def federation():
    served = {"config": _configuration()}

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == f"/ep/{CONFIG_ID}/netbird":
                # Federation 1.12.10: only the owner's token gets the key.
                if self.headers.get("Authorization") != f"Bearer {OWNER_TOKEN}":
                    self.send_response(403)
                    self.end_headers()
                    return
                data = json.dumps(
                    {"management_url": MANAGEMENT_URL, "setup_key": FEDERATION_KEY}
                ).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
                return
            if self.path != f"/ep/{CONFIG_ID}":
                self.send_response(404)
                self.end_headers()
                return
            data = json.dumps(served["config"]).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, *args):
            pass

    server = HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    served["url"] = f"http://127.0.0.1:{server.server_address[1]}"
    yield served
    server.shutdown()


@pytest.fixture
def host(tmp_path):
    """A checkout plus stub netbird/sudo/docker that record what they are asked."""
    checkout = tmp_path / "ep-api"
    shutil.copytree(REPO / "install", checkout / "install")
    shutil.copy(REPO / "example.env", checkout / "example.env")
    shutil.copy(REPO / "docker-compose.yml", checkout / "docker-compose.yml")
    stubs = tmp_path / "bin"
    stubs.mkdir()
    log = tmp_path / "netbird.log"
    joined = tmp_path / "netbird.joined"
    (stubs / "netbird").write_text(
        "#!/bin/sh\n"
        f'echo "netbird $*" >> "{log}"\n'
        'case "$1" in\n'
        "  status)\n"
        f'    if [ -f "{joined}" ]; then\n'
        f'      printf \'{{"management":{{"url":"{MANAGEMENT_URL}","connected":true}},'
        '"netbirdIp":"100.64.0.7/16"}\'\n'
        "    else\n"
        '      printf \'{"management":{"url":"","connected":false},"netbirdIp":""}\'\n'
        "    fi ;;\n"
        "  up)\n"
        "    while [ $# -gt 0 ]; do\n"
        '      [ "$1" = "--setup-key-file" ] && [ -r "$2" ] && '
        f'cp "$2" "{tmp_path}/key.seen"\n'
        "      shift\n"
        "    done\n"
        f'    touch "{joined}" ;;\n'
        "esac\n",
        encoding="utf-8",
    )
    (stubs / "sudo").write_text('#!/bin/sh\nexec "$@"\n', encoding="utf-8")
    (stubs / "docker").write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    for stub in stubs.iterdir():
        stub.chmod(0o755)
    key_file = tmp_path / "setup-key"
    key_file.write_text(SETUP_KEY, encoding="utf-8")
    return {
        "checkout": checkout,
        "stubs": stubs,
        "log": log,
        "key": key_file,
        "tmp": tmp_path,
    }


def _install(host, federation, *args):
    return subprocess.run(
        [
            BASH,
            str(host["checkout"] / "install" / "install.sh"),
            "--config-id",
            CONFIG_ID,
            "--federation-url",
            federation["url"],
            "--backend",
            "none",
            *args,
            "--yes",
            "--no-start",
        ],
        capture_output=True,
        text=True,
        timeout=120,
        env={**os.environ, "PATH": f"{host['stubs']}{os.pathsep}{os.environ['PATH']}"},
        stdin=subprocess.DEVNULL,
    )


def _env(host):
    text = (host["checkout"] / ".env").read_text(encoding="utf-8")
    return dict(
        line.split("=", 1) for line in text.splitlines() if re.match(r"^[A-Z_]+=", line)
    )


def _netbird_calls(host):
    return host["log"].read_text(encoding="utf-8") if host["log"].exists() else ""


def test_without_the_flags_nothing_changes(host, federation):
    federation["config"] = _configuration(
        netbird_management_url=MANAGEMENT_URL,
        affinities_url="https://affinities.example.org",
        affinities_uid="aff-uid-1",
    )

    result = _install(host, federation)

    assert result.returncode == 0, result.stdout + result.stderr
    env = _env(host)
    assert env["NETBIRD_ENABLED"] == "False"
    assert env["AFFINITIES_ENABLED"] == "False"
    assert _netbird_calls(host) == ""


def test_netbird_joins_with_the_federation_url_and_the_key_file(host, federation):
    federation["config"] = _configuration(netbird_management_url=MANAGEMENT_URL)

    result = _install(host, federation, "--netbird-setup-key-file", str(host["key"]))

    assert result.returncode == 0, result.stdout + result.stderr
    calls = _netbird_calls(host)
    assert f"netbird up --management-url {MANAGEMENT_URL} --setup-key-file" in calls
    assert (host["tmp"] / "key.seen").read_text() == SETUP_KEY
    env = _env(host)
    assert env["NETBIRD_ENABLED"] == "True"
    assert env["NETBIRD_IP"] == "100.64.0.7"


def test_the_setup_key_is_never_written_or_printed(host, federation):
    federation["config"] = _configuration(netbird_management_url=MANAGEMENT_URL)

    result = _install(host, federation, "--netbird-setup-key-file", str(host["key"]))

    assert SETUP_KEY not in result.stdout + result.stderr
    assert SETUP_KEY not in _netbird_calls(host)
    for name in (".env", ".env.install-state"):
        assert SETUP_KEY not in (host["checkout"] / name).read_text(encoding="utf-8")


def test_a_re_run_keeps_netbird_without_the_key(host, federation):
    federation["config"] = _configuration(netbird_management_url=MANAGEMENT_URL)
    _install(host, federation, "--netbird-setup-key-file", str(host["key"]))
    host["log"].unlink()

    result = _install(host, federation)

    assert result.returncode == 0, result.stdout + result.stderr
    assert "netbird up" not in _netbird_calls(host)
    assert _env(host)["NETBIRD_ENABLED"] == "True"
    assert _env(host)["NETBIRD_IP"] == "100.64.0.7"


def test_the_management_url_can_be_overridden(host, federation):
    federation["config"] = _configuration(netbird_management_url=MANAGEMENT_URL)

    _install(
        host,
        federation,
        "--netbird-setup-key-file",
        str(host["key"]),
        "--netbird-management-url",
        "https://other.example.org",
    )

    assert "--management-url https://other.example.org" in _netbird_calls(host)


def test_netbird_without_a_management_url_stops(host, federation):
    result = _install(host, federation, "--netbird-setup-key-file", str(host["key"]))

    assert result.returncode == 1
    assert "needs the NetBird management URL" in result.stderr


def test_netbird_without_a_key_stops_when_not_connected(host, federation):
    federation["config"] = _configuration(netbird_management_url=MANAGEMENT_URL)

    result = _install(host, federation, "--netbird")

    assert result.returncode == 1
    assert "--ndp-token-file" in result.stderr


def test_affinities_is_turned_on_from_the_configuration(host, federation):
    federation["config"] = _configuration(
        affinities_url="https://affinities.example.org", affinities_uid="aff-uid-1"
    )

    result = _install(host, federation, "--affinities")

    assert result.returncode == 0, result.stdout + result.stderr
    env = _env(host)
    assert env["AFFINITIES_ENABLED"] == "True"
    assert env["AFFINITIES_URL"] == "https://affinities.example.org"
    assert env["AFFINITIES_EP_UUID"] == "aff-uid-1"

    again = _install(host, federation)
    assert again.returncode == 0, again.stdout + again.stderr
    assert _env(host)["AFFINITIES_ENABLED"] == "True"


def test_affinities_without_an_id_stops(host, federation):
    federation["config"] = _configuration(
        affinities_url="https://affinities.example.org"
    )

    result = _install(host, federation, "--affinities")

    assert result.returncode == 1
    assert "--affinities needs a Federation registration" in result.stderr


def test_the_key_comes_from_the_federation_with_the_owners_token(host, federation):
    """Issue #361: the person installing never sees the key."""
    federation["config"] = _configuration(netbird_management_url=MANAGEMENT_URL)
    token_file = host["tmp"] / "ndp-token"
    token_file.write_text(OWNER_TOKEN + "\n", encoding="utf-8")

    result = _install(
        host, federation, "--netbird", "--ndp-token-file", str(token_file)
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert (host["tmp"] / "key.seen").read_text() == FEDERATION_KEY
    assert _env(host)["NETBIRD_ENABLED"] == "True"
    for secret in (FEDERATION_KEY, OWNER_TOKEN):
        assert secret not in result.stdout + result.stderr
        assert secret not in _netbird_calls(host)
        for name in (".env", ".env.install-state"):
            text = (host["checkout"] / name).read_text(encoding="utf-8")
            assert secret not in text


def test_a_token_that_does_not_own_the_configuration_stops(host, federation):
    federation["config"] = _configuration(netbird_management_url=MANAGEMENT_URL)
    token_file = host["tmp"] / "ndp-token"
    token_file.write_text("someone-elses-token", encoding="utf-8")

    result = _install(
        host, federation, "--netbird", "--ndp-token-file", str(token_file)
    )

    assert result.returncode == 1
    assert "does not own configuration" in result.stderr
    assert "netbird up" not in _netbird_calls(host)
