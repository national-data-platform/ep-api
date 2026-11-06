"""
The Endpoint's port is written to .env (issue #370).

The installer passed ``EP_API_PORT`` only on the ``docker compose`` command
line, so restarting an Endpoint by hand with ``docker compose up`` in its
checkout published it on the default 8002: on a host with two Endpoints the
second one failed with "port is already allocated", and a single Endpoint on
another port would silently move. The other host ports of a named instance
were already in ``.env``; now the API's own port is too.

The run is the real installer with ``--dry-run``; ``docker`` is a stub and
``curl`` never leaves the machine, as in ``test_test_token_blank.py``.
"""

import os
import shutil
import subprocess
from pathlib import Path

import pytest

INSTALL_DIR = Path(__file__).resolve().parents[1]
INSTALLER = INSTALL_DIR / "install.sh"

BASH = shutil.which("bash")

pytestmark = pytest.mark.skipif(
    BASH is None or os.name == "nt",
    reason="needs bash; the stubs are POSIX shell scripts",
)


@pytest.fixture
def stub_path(tmp_path):
    for name, body in (("docker", "exit 0"), ("curl", "printf 000\nexit 7")):
        stub = tmp_path / name
        stub.write_text(f"#!/bin/sh\n{body}\n", encoding="utf-8")
        stub.chmod(0o755)
    return f"{tmp_path}{os.pathsep}{os.environ['PATH']}"


def _rendered_lines(stub_path, *args):
    result = subprocess.run(
        [BASH, str(INSTALLER), "--backend", "none", "--dry-run", "--yes", *args],
        capture_output=True,
        text=True,
        timeout=120,
        env={**os.environ, "PATH": stub_path},
        stdin=subprocess.DEVNULL,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return result.stdout.splitlines()


def test_a_chosen_port_is_written_to_env(stub_path):
    lines = _rendered_lines(stub_path, "--ep-api-port", "8123")

    assert "EP_API_PORT=8123" in lines


def test_the_default_port_is_written_too(stub_path):
    """Written even when it is the default, so .env says what is published."""
    lines = _rendered_lines(stub_path)

    assert [line for line in lines if line.startswith("EP_API_PORT=")] == [
        "EP_API_PORT=8002"
    ]
