"""
Choosing the bundled MinIO drops an S3 endpoint remembered from before (#345).

Remembered settings can hold the endpoint of an S3 service an earlier run
used. Choosing "MinIO, installed alongside the Endpoint" afterwards left that
endpoint set, so the installer took the existing-S3 branch with no keys and
stopped with "--s3-endpoint requires --s3-access-key and --s3-secret-key".

The prompts only appear on a terminal, so the installer runs under a
pseudo-terminal against a stand-in Federation on localhost.
"""

import json
import os
import pty
import select
import shutil
import subprocess
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
BASH = shutil.which("bash")

pytestmark = pytest.mark.skipif(
    BASH is None or os.name == "nt" or shutil.which("curl") is None,
    reason="needs bash, curl and a pseudo-terminal",
)

CONFIG_ID = "cfg345"
REMEMBERED = {
    "settings": {
        "want_s3": "yes",
        "s3_endpoint": "s3.example.org:9000",
        "s3_secure": "True",
    }
}
REGISTRATION = {"organization": "ORG-345", "ep_name": "EP-345"}


class StandInFederation(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == f"/ep/{CONFIG_ID}/settings":
            body = REMEMBERED
        elif self.path == f"/ep/{CONFIG_ID}":
            body = REGISTRATION
        else:
            self.send_response(404)
            self.end_headers()
            return
        data = json.dumps(body).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_PUT(self):
        self.send_response(200)
        self.end_headers()

    def log_message(self, *args):
        pass


@pytest.fixture
def federation():
    server = HTTPServer(("127.0.0.1", 0), StandInFederation)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()


def _answer(line):
    """What an operator who wants the bundled MinIO types at each prompt."""
    if "Federation configuration to remember" in line:
        return "y"
    if "NDP access token" in line:
        return "token-345"
    if "Enable S3 object storage" in line:
        return "y"
    if "Choice" in line and "Which S3" in _answer.last_question:
        return "1"
    return ""


_answer.last_question = ""


def _run_installer(checkout, federation, stubs):
    env = {
        **os.environ,
        "PATH": f"{stubs}{os.pathsep}{os.environ['PATH']}",
        "TERM": "dumb",
    }
    main, child = pty.openpty()
    process = subprocess.Popen(
        [
            BASH,
            str(checkout / "install" / "install.sh"),
            "--config-id",
            CONFIG_ID,
            "--federation-url",
            federation,
            "--dry-run",
        ],
        stdin=child,
        stdout=child,
        stderr=child,
        env=env,
        cwd=checkout,
        close_fds=True,
    )
    os.close(child)

    output, pending = "", ""
    deadline = time.time() + 120
    while time.time() < deadline:
        ready, _, _ = select.select([main], [], [], 0.5)
        if ready:
            try:
                chunk = os.read(main, 4096).decode(errors="replace")
            except OSError:
                break
            if not chunk:
                break
            output += chunk
            pending += chunk
            for line in pending.splitlines():
                if "?" in line or "Which" in line:
                    _answer.last_question = line
            last = pending.rstrip(" ").splitlines()[-1] if pending.strip() else ""
            if last.endswith(":") or last.endswith("]:"):
                os.write(main, (_answer(last) + "\n").encode())
                pending = ""
        elif process.poll() is not None:
            break
    process.wait(timeout=30)
    os.close(main)
    return process.returncode, output


def test_choosing_minio_after_a_remembered_endpoint_installs_minio(
    federation, tmp_path
):
    checkout = tmp_path / "ep-api"
    shutil.copytree(REPO / "install", checkout / "install")
    shutil.copy(REPO / "example.env", checkout / "example.env")
    stubs = tmp_path / "bin"
    stubs.mkdir()
    (stubs / "docker").write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    (stubs / "docker").chmod(0o755)

    code, output = _run_installer(checkout, federation, stubs)

    assert "Loaded the settings remembered" in output, output
    assert "requires --s3-access-key" not in output, output
    assert "installing MinIO" in output, output
    assert code == 0, output
