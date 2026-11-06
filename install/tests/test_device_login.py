"""
install/device_login.py signs the user in with the OAuth device flow
(issue #397). A stand-in realm answers the two device-flow endpoints.
"""

import json
import subprocess
import sys
import threading
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "device_login.py"
CLIENT = "ndp-installer"
TOKEN = "access-token-from-the-device-flow"


@pytest.fixture
def realm():
    state = {"answers": [], "calls": []}

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            length = int(self.headers.get("Content-Length") or 0)
            form = dict(urllib.parse.parse_qsl(self.rfile.read(length).decode()))
            state["calls"].append((self.path, form))
            if self.path.endswith("/auth/device"):
                if form.get("client_id") != CLIENT:
                    status, body = 401, {"error": "invalid_client"}
                else:
                    status, body = 200, {
                        "device_code": "dev-1",
                        "user_code": "ABCD-EFGH",
                        "verification_uri": "https://idp.example/device",
                        "verification_uri_complete": "https://idp.example/device?code=ABCD-EFGH",
                        "expires_in": 600,
                        "interval": 0,
                    }
            else:
                status, body = state["answers"].pop(0)
            data = json.dumps(body).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, *args):
            pass

    server = HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    state["issuer"] = f"http://127.0.0.1:{server.server_address[1]}/realms/NDP"
    yield state
    server.shutdown()


def _login(issuer, client=CLIENT, timeout="30"):
    return subprocess.run(
        [sys.executable, str(SCRIPT), issuer, client, timeout],
        capture_output=True,
        text=True,
        timeout=60,
    )


def test_prints_only_the_token_once_signed_in(realm):
    realm["answers"] = [
        (400, {"error": "authorization_pending"}),
        (400, {"error": "slow_down"}),
        (200, {"access_token": TOKEN}),
    ]

    result = _login(realm["issuer"])

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == TOKEN
    assert TOKEN not in result.stderr
    assert "https://idp.example/device?code=ABCD-EFGH" in result.stderr
    assert "ABCD-EFGH" in result.stderr


def test_polls_the_token_endpoint_with_the_device_grant(realm):
    realm["answers"] = [(200, {"access_token": TOKEN})]

    _login(realm["issuer"])

    path, form = realm["calls"][-1]
    assert path == "/realms/NDP/protocol/openid-connect/token"
    assert form == {
        "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
        "client_id": CLIENT,
        "device_code": "dev-1",
    }


@pytest.mark.parametrize("error", ["access_denied", "expired_token"])
def test_a_sign_in_not_completed_is_exit_1(realm, error):
    realm["answers"] = [(400, {"error": error})]

    result = _login(realm["issuer"])

    assert result.returncode == 1
    assert result.stdout == ""


def test_an_unknown_client_is_exit_2(realm):
    result = _login(realm["issuer"], client="nope")

    assert result.returncode == 2
    assert "invalid_client" in result.stderr
    assert result.stdout == ""


def test_an_unreachable_realm_is_exit_2():
    result = _login("http://127.0.0.1:9/realms/NDP")

    assert result.returncode == 2
    assert "could not reach" in result.stderr
