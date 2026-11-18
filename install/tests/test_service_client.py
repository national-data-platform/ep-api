"""
The installer keeps the Endpoint's service client from its registration
(issue #412, follow-up to #411).

Registering an Endpoint creates a confidential Keycloak client,
``ep-<config-id>``, and the Federation hands its id and secret to the
Endpoint's owner. The installer read the id, printed it and dropped both, so
the Endpoint had no way to get a client-credentials token. They now go to
``OIDC_SERVICE_CLIENT_ID`` / ``OIDC_SERVICE_CLIENT_SECRET``, which are separate
from the browser sign-in client (``OIDC_CLIENT_ID``), and the secret is never
printed.

Each test runs the real installer with ``--dry-run`` against a Federation
served from this process; ``docker`` is a stub and ``curl`` only reaches
127.0.0.1.
"""

import json
import os
import shutil
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

INSTALLER = Path(__file__).resolve().parents[1] / "install.sh"
CONFIG_ID = "0123456789abcdef01234567"
SECRET = "s3cr3t-Value-0f-the-client"

BASH = shutil.which("bash")
REAL_CURL = shutil.which("curl")

pytestmark = pytest.mark.skipif(
    BASH is None or REAL_CURL is None or os.name == "nt",
    reason="needs bash and curl; the stubs are POSIX shell scripts",
)


def _federation_answering(config):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802 - the http.server naming
            if self.path.rstrip("/").endswith(f"/ep/{CONFIG_ID}"):
                body = json.dumps(config).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(body)
            else:
                self.send_response(404)
                self.end_headers()

        def log_message(self, *args):
            pass

    return Handler


BASE = {
    "organization": "Test-Org",
    "ep_name": "test-ep",
    "group_name": f"ndp_ep/ep-{CONFIG_ID}",
    "public": True,
    "streaming": False,
    "jhub": False,
}


@pytest.fixture
def federation():
    servers = []

    def serve(config):
        server = HTTPServer(("127.0.0.1", 0), _federation_answering(config))
        threading.Thread(target=server.serve_forever, daemon=True).start()
        servers.append(server)
        return f"http://127.0.0.1:{server.server_port}"

    yield serve
    for server in servers:
        server.shutdown()


@pytest.fixture(scope="module")
def stub_path(tmp_path_factory):
    stub_dir = tmp_path_factory.mktemp("stub-bin")
    docker = stub_dir / "docker"
    docker.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    docker.chmod(0o755)
    curl = stub_dir / "curl"
    curl.write_text(
        "#!/bin/sh\n"
        'case "$*" in\n'
        f'  *127.0.0.1*) exec "{REAL_CURL}" "$@" ;;\n'
        "esac\n"
        "printf 000\n"
        "exit 7\n",
        encoding="utf-8",
    )
    curl.chmod(0o755)
    return f"{stub_dir}{os.pathsep}{os.environ['PATH']}"


def _run(stub_path, url):
    result = subprocess.run(
        [
            BASH,
            str(INSTALLER),
            "--backend",
            "none",
            "--dry-run",
            "--yes",
            "--config-id",
            CONFIG_ID,
            "--federation-url",
            url,
        ],
        capture_output=True,
        text=True,
        timeout=120,
        env={**os.environ, "PATH": stub_path},
        stdin=subprocess.DEVNULL,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    env = dict(
        line.split("=", 1)
        for line in result.stdout.splitlines()
        if "=" in line and line.split("=", 1)[0].isupper()
    )
    return env, result.stdout + result.stderr


def test_the_registration_s_client_becomes_the_service_client(federation, stub_path):
    url = federation(dict(BASE, client_id=f"ep-{CONFIG_ID}", client_secret=SECRET))

    env, _ = _run(stub_path, url)

    assert env["OIDC_SERVICE_CLIENT_ID"] == f"ep-{CONFIG_ID}"
    assert "OIDC_SERVICE_CLIENT_SECRET" in env


def test_the_secret_is_never_printed(federation, stub_path):
    url = federation(dict(BASE, client_id=f"ep-{CONFIG_ID}", client_secret=SECRET))

    env, output = _run(stub_path, url)

    assert SECRET not in output
    assert env["OIDC_SERVICE_CLIENT_SECRET"] != SECRET


def test_the_sign_in_client_is_left_alone(federation, stub_path):
    """The service client is confidential; browser sign-in needs a public one."""
    url = federation(dict(BASE, client_id=f"ep-{CONFIG_ID}", client_secret=SECRET))

    env, _ = _run(stub_path, url)

    assert "OIDC_CLIENT_ID" not in env
    assert env["OIDC_ENABLED"] == "False"


def test_a_registration_without_a_client_writes_none(federation, stub_path):
    url = federation(BASE)

    env, _ = _run(stub_path, url)

    # example.env lists both keys, so they are present but empty.
    assert env.get("OIDC_SERVICE_CLIENT_ID", "") == ""
    assert env.get("OIDC_SERVICE_CLIENT_SECRET", "") == ""


def test_the_placeholder_client_of_a_failed_registration_is_not_kept(
    federation, stub_path
):
    """A registration whose Keycloak step failed carries default-ep-client
    and no secret (sci-ndp/ndp-federation#138); it is not this Endpoint's."""
    url = federation(dict(BASE, client_id="default-ep-client", client_secret=""))

    env, output = _run(stub_path, url)

    assert env.get("OIDC_SERVICE_CLIENT_ID", "") == ""
    assert "default-ep-client" in output
