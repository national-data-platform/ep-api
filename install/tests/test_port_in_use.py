"""
A port that is in use is reported, not swallowed (issue #313).

Each port probe was followed by ``exec 3>&- 2>/dev/null``. The probe opens its
descriptor in a subshell, so there was nothing to close, and the line's only
lasting effect was to send stderr to /dev/null for the rest of the run: the
installer then failed on a busy port with status 1 and no message.
"""

import os
import re
import shutil
import socket
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
INSTALLER = REPO / "install" / "install.sh"
BASH = shutil.which("bash")

pytestmark = pytest.mark.skipif(
    BASH is None or os.name == "nt",
    reason="needs bash with /dev/tcp; the stubs are POSIX shell scripts",
)


@pytest.fixture
def busy_port():
    with socket.socket() as server:
        server.bind(("127.0.0.1", 0))
        server.listen()
        yield server.getsockname()[1]


def _port_free_function():
    text = INSTALLER.read_text(encoding="utf-8")
    return re.search(r"^port_free\(\) \{.*?^\}", text, re.S | re.M).group(0)


def test_probing_a_busy_port_leaves_stderr_working(busy_port):
    script = (
        "set -euo pipefail\n"
        f"{_port_free_function()}\n"
        f"port_free {busy_port} || true\n"
        "echo still-visible >&2\n"
    )

    result = subprocess.run(
        [BASH, "-c", script], capture_output=True, text=True, timeout=30
    )

    assert "still-visible" in result.stderr


def test_the_installer_says_why_it_stops_on_a_busy_port(busy_port, tmp_path):
    """The whole installer, run on a copy of the repository."""
    checkout = tmp_path / "ep-api"
    shutil.copytree(REPO / "install", checkout / "install")
    shutil.copy(REPO / "example.env", checkout / "example.env")

    stubs = tmp_path / "bin"
    stubs.mkdir()
    (stubs / "docker").write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    # Nothing leaves the machine: the authentication probe gets no answer.
    (stubs / "curl").write_text("#!/bin/sh\nprintf 000\nexit 7\n", encoding="utf-8")
    for stub in stubs.iterdir():
        stub.chmod(0o755)

    result = subprocess.run(
        [
            BASH,
            str(checkout / "install" / "install.sh"),
            "--backend",
            "none",
            "--ep-api-port",
            str(busy_port),
            "--yes",
        ],
        capture_output=True,
        text=True,
        timeout=120,
        env={**os.environ, "PATH": f"{stubs}{os.pathsep}{os.environ['PATH']}"},
        stdin=subprocess.DEVNULL,
    )

    assert result.returncode == 1
    assert f"Port {busy_port} is already in use" in result.stderr
