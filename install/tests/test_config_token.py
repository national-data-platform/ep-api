"""
The installer sends the user's NDP token when it reads the configuration
(issue #397).

Federation 2.0.0 answers ``GET /ep/{config_id}`` only to an admin of the
Endpoint, from the Bearer token (sci-ndp/ndp-federation#130); older
Federations answer without one. A stand-in Federation plays either.
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

CONFIG_ID = "cfg397"
ADMIN_TOKEN = "admin-ndp-token-397"
OTHER_TOKEN = "someone-elses-token-397"


def _federation(gated):
    seen = {"auth": []}

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path != f"/ep/{CONFIG_ID}":
                self.send_response(404)
                self.end_headers()
                return
            auth = self.headers.get("Authorization")
            seen["auth"].append(auth)
            if gated and auth is None:
                status = 401
            elif gated and auth == f"Bearer {OTHER_TOKEN}":
                status = 403
            elif gated and auth != f"Bearer {ADMIN_TOKEN}":
                status = 401
            else:
                status = 200
            data = json.dumps(
                {
                    "_id": CONFIG_ID,
                    "organization": "ORG-397",
                    "ep_name": "EP-397",
                    "group_name": "ndp_ep/ep-cfg397",
                }
                if status == 200
                else {"detail": "no"}
            ).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, *args):
            pass

    server = HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    seen["url"] = f"http://127.0.0.1:{server.server_address[1]}"
    return server, seen


@pytest.fixture
def gated_federation():
    server, seen = _federation(gated=True)
    yield seen
    server.shutdown()


@pytest.fixture
def open_federation():
    server, seen = _federation(gated=False)
    yield seen
    server.shutdown()


@pytest.fixture
def checkout(tmp_path):
    root = tmp_path / "ep-api"
    shutil.copytree(REPO / "install", root / "install")
    shutil.copy(REPO / "example.env", root / "example.env")
    shutil.copy(REPO / "docker-compose.yml", root / "docker-compose.yml")
    stubs = tmp_path / "bin"
    stubs.mkdir()
    (stubs / "docker").write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    (stubs / "docker").chmod(0o755)
    return {"root": root, "stubs": stubs, "tmp": tmp_path}


def _install(checkout, federation, *args):
    return subprocess.run(
        [
            BASH,
            str(checkout["root"] / "install" / "install.sh"),
            "--config-id",
            CONFIG_ID,
            "--federation-url",
            federation["url"],
            "--backend",
            "none",
            "--no-netbird",
            *args,
            "--yes",
            "--no-start",
        ],
        capture_output=True,
        text=True,
        timeout=120,
        env={
            **os.environ,
            "PATH": f"{checkout['stubs']}{os.pathsep}{os.environ['PATH']}",
        },
        stdin=subprocess.DEVNULL,
    )


def _token_file(checkout, token):
    path = checkout["tmp"] / "ndp-token"
    path.write_text(token + "\n", encoding="utf-8")
    return str(path)


def _env(checkout):
    text = (checkout["root"] / ".env").read_text(encoding="utf-8")
    return dict(
        line.split("=", 1) for line in text.splitlines() if re.match(r"^[A-Z_]+=", line)
    )


def test_an_older_federation_is_read_without_a_token(checkout, open_federation):
    result = _install(checkout, open_federation)

    assert result.returncode == 0, result.stdout + result.stderr
    assert open_federation["auth"] == [None]
    assert _env(checkout)["EP_NAME"] == "EP-397"


def test_the_token_file_is_sent_to_a_gated_federation(checkout, gated_federation):
    result = _install(
        checkout,
        gated_federation,
        "--ndp-token-file",
        _token_file(checkout, ADMIN_TOKEN),
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert gated_federation["auth"] == [f"Bearer {ADMIN_TOKEN}"]
    assert _env(checkout)["EP_NAME"] == "EP-397"


def test_the_token_is_never_printed_or_written(checkout, gated_federation):
    result = _install(
        checkout,
        gated_federation,
        "--ndp-token-file",
        _token_file(checkout, ADMIN_TOKEN),
    )

    assert ADMIN_TOKEN not in result.stdout + result.stderr
    for name in (".env", ".env.install-state"):
        path = checkout["root"] / name
        if path.exists():
            assert ADMIN_TOKEN not in path.read_text(encoding="utf-8")


def test_without_a_token_it_says_how_to_give_one(checkout, gated_federation):
    result = _install(checkout, gated_federation)

    assert result.returncode == 1
    assert "needs your NDP access token" in result.stderr
    assert "--ndp-token-file" in result.stderr
    assert "HTTP 401" not in result.stderr


def test_a_token_of_someone_else_is_named_as_such(checkout, gated_federation):
    result = _install(
        checkout,
        gated_federation,
        "--ndp-token-file",
        _token_file(checkout, OTHER_TOKEN),
    )

    assert result.returncode == 1
    assert f"not an admin of configuration {CONFIG_ID}" in result.stderr


def test_a_rejected_token_is_named_as_such(checkout, gated_federation):
    result = _install(
        checkout, gated_federation, "--ndp-token-file", _token_file(checkout, "expired")
    )

    assert result.returncode == 1
    assert "did not accept your NDP access token" in result.stderr


def test_the_login_options_are_documented():
    usage = subprocess.run(
        [BASH, str(REPO / "install" / "install.sh"), "--help"],
        capture_output=True,
        text=True,
        timeout=30,
    ).stdout
    assert "--login-client-id <id>" in usage
    assert "--login-issuer <url>" in usage


def test_an_unreachable_federation_is_named_as_such(checkout):
    result = _install(checkout, {"url": "http://127.0.0.1:9"})

    assert result.returncode == 1
    assert "Could not reach the Federation" in result.stderr
    assert "000000" not in result.stderr
