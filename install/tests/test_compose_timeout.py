"""
A stalled ``docker compose up`` no longer hangs the installer (issue #376).

The start step and the CKAN build ran ``docker compose up -d --build`` with no
limit, so a pull stuck on a registry, a rate limit or a proxy kept the run
waiting for ever after every earlier step had reported success. Both now run
under ``--compose-timeout`` (30 minutes unless given), and running out of time
stops the run with what to check.

``docker`` is a stub whose ``compose up`` never returns (or fails at once), so
nothing is pulled or built.
"""

import os
import shutil
import socket
import subprocess
import time
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
BASH = shutil.which("bash")

pytestmark = pytest.mark.skipif(
    BASH is None or os.name == "nt" or shutil.which("timeout") is None,
    reason="needs bash and coreutils timeout",
)


def _free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _checkout(tmp_path, up_behaviour):
    root = tmp_path / "ep-api"
    shutil.copytree(REPO / "install", root / "install")
    shutil.copy(REPO / "example.env", root / "example.env")
    shutil.copy(REPO / "docker-compose.yml", root / "docker-compose.yml")
    stubs = tmp_path / "bin"
    stubs.mkdir()
    (stubs / "docker").write_text(
        "#!/bin/sh\n"
        f'echo "docker $*" >> "{tmp_path}/docker.log"\n'
        'case " $* " in\n'
        f"  *' up '*) {up_behaviour} ;;\n"
        "esac\n"
        "exit 0\n",
        encoding="utf-8",
    )
    (stubs / "docker").chmod(0o755)
    return root, stubs


def _install(root, stubs, *args):
    started = time.monotonic()
    result = subprocess.run(
        [
            BASH,
            str(root / "install" / "install.sh"),
            "--backend",
            "none",
            "--no-netbird",
            "--ep-api-port",
            str(_free_port()),
            "--yes",
            *args,
        ],
        capture_output=True,
        text=True,
        timeout=120,
        env={**os.environ, "PATH": f"{stubs}{os.pathsep}{os.environ['PATH']}"},
        stdin=subprocess.DEVNULL,
    )
    return result, time.monotonic() - started


def test_a_stalled_compose_up_stops_the_run(tmp_path):
    root, stubs = _checkout(tmp_path, "exec sleep 300")

    result, took = _install(root, stubs, "--compose-timeout", "3s")

    assert result.returncode != 0
    assert took < 60
    assert "did not finish within 3s" in result.stderr


def test_the_timeout_message_says_what_to_check(tmp_path):
    root, stubs = _checkout(tmp_path, "exec sleep 300")

    result, _ = _install(root, stubs, "--compose-timeout", "3s")

    assert "docker pull" in result.stderr
    assert "rate limit" in result.stderr
    assert "--compose-timeout" in result.stderr


def test_a_compose_that_fails_is_not_reported_as_a_timeout(tmp_path):
    root, stubs = _checkout(tmp_path, "exit 3")

    result, _ = _install(root, stubs, "--compose-timeout", "30s")

    assert result.returncode != 0
    assert "did not finish" not in result.stderr
    assert "could not start the Endpoint" in result.stderr


@pytest.mark.parametrize("value", ["abc", "-5", "10x", ""])
def test_a_malformed_timeout_is_refused(tmp_path, value):
    root, stubs = _checkout(tmp_path, "exit 0")

    result, _ = _install(root, stubs, "--compose-timeout", value)

    assert result.returncode != 0
    assert "--compose-timeout" in result.stderr


def test_minutes_are_the_unit_without_a_suffix(tmp_path):
    root, stubs = _checkout(tmp_path, "exit 3")

    result, _ = _install(root, stubs, "--compose-timeout", "45")

    assert "--compose-timeout must be" not in result.stderr
    assert "Docker Compose time limit: 45 min" in result.stdout


def test_thirty_minutes_unless_given(tmp_path):
    root, stubs = _checkout(tmp_path, "exit 3")

    result, _ = _install(root, stubs)

    assert "Docker Compose time limit: 30 min" in result.stdout


def test_zero_means_no_limit(tmp_path):
    root, stubs = _checkout(tmp_path, "exit 3")

    result, _ = _install(root, stubs, "--compose-timeout", "0")

    assert "Docker Compose time limit: none" in result.stdout
    assert "could not start the Endpoint" in result.stderr
