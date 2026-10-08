"""
Metrics go to the Federation the installer was pointed at (issue #307).

``--env`` and ``--federation-url`` decided where the installer registered and
fetched its configuration, but ``METRICS_ENDPOINT`` was never written, so it
kept ``example.env``'s production value and an Endpoint registered with the
test Federation reported to production.

Each test runs the real installer with ``--dry-run`` against a Federation
served from this process, which answers ``GET /ep/{id}`` with a minimal
configuration. ``docker`` is a stub that answers the prerequisite checks, and
``curl`` is wrapped so that anything other than the local Federation fails at
once: the run never leaves the machine.
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
PROD_METRICS = "https://federation.ndp.utah.edu/metrics/"

BASH = shutil.which("bash")
REAL_CURL = shutil.which("curl")

pytestmark = pytest.mark.skipif(
    BASH is None or REAL_CURL is None or os.name == "nt",
    reason="needs bash and curl; the stubs are POSIX shell scripts",
)


class _Federation(BaseHTTPRequestHandler):
    """Answers GET /ep/<CONFIG_ID> like the Federation does."""

    def do_GET(self):  # noqa: N802 - the http.server naming
        if self.path.rstrip("/").endswith(f"/ep/{CONFIG_ID}"):
            body = json.dumps(
                {
                    "organization": "Test-Org",
                    "ep_name": "test-ep",
                    "group_name": f"ndp_ep/ep-{CONFIG_ID}",
                    "public": True,
                    "streaming": False,
                    "jhub": False,
                }
            ).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, *args):
        pass


@pytest.fixture(scope="module")
def federation():
    server = HTTPServer(("127.0.0.1", 0), _Federation)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}"
    server.shutdown()


@pytest.fixture(scope="module")
def stub_path(tmp_path_factory):
    """docker that answers the checks; curl that only reaches 127.0.0.1."""
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


def _rendered(stub_path, *args):
    result = subprocess.run(
        [BASH, str(INSTALLER), "--backend", "none", "--dry-run", "--yes", *args],
        capture_output=True,
        text=True,
        timeout=120,
        env={**os.environ, "PATH": stub_path},
        stdin=subprocess.DEVNULL,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return dict(
        line.split("=", 1)
        for line in result.stdout.splitlines()
        if "=" in line and line.split("=", 1)[0].isupper()
    )


def test_metrics_follow_the_federation_the_endpoint_registered_with(
    federation, stub_path
):
    env = _rendered(stub_path, "--config-id", CONFIG_ID, "--federation-url", federation)

    assert env["METRICS_ENDPOINT"] == f"{federation}/metrics/"
    assert env["IS_PUBLIC"] == "True"


def test_a_trailing_slash_on_the_url_does_not_double_up(federation, stub_path):
    env = _rendered(
        stub_path, "--config-id", CONFIG_ID, "--federation-url", federation + "/"
    )

    assert env["METRICS_ENDPOINT"] == f"{federation}/metrics/"


def test_without_a_federation_choice_metrics_go_to_production(stub_path):
    env = _rendered(stub_path)

    assert env["METRICS_ENDPOINT"] == PROD_METRICS
    assert env["IS_PUBLIC"] == "False"
