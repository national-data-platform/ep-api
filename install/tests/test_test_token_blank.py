"""
An installed Endpoint never accepts the development test token (issue #383).

``example.env`` used to set ``TEST_TOKEN=testing_token`` and the installer
renders ``.env`` from it, so every installer-made Endpoint accepted that public
value as a platform administrator. The installer now writes ``TEST_TOKEN``
empty itself, so it stays off even if ``example.env`` changes again.

The run is the real installer with ``--dry-run``; ``docker`` is a stub and
``curl`` never leaves the machine, as in ``test_metrics_endpoint.py``.
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


def _rendered_lines(stub_path):
    result = subprocess.run(
        [BASH, str(INSTALLER), "--backend", "none", "--dry-run", "--yes"],
        capture_output=True,
        text=True,
        timeout=120,
        env={**os.environ, "PATH": stub_path},
        stdin=subprocess.DEVNULL,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return result.stdout.splitlines()


def test_installer_writes_test_token_empty(stub_path):
    lines = _rendered_lines(stub_path)

    assert "TEST_TOKEN=" in lines
    assert not any(
        line.startswith("TEST_TOKEN=") and line != "TEST_TOKEN=" for line in lines
    )


def test_installer_overrides_a_non_empty_example_value(stub_path, tmp_path):
    """Even if example.env sets a value again, the installed .env has none."""
    repo = INSTALL_DIR.parent
    copy = tmp_path / "repo"
    shutil.copytree(
        INSTALL_DIR,
        copy / "install",
        ignore=shutil.ignore_patterns("tests", "__pycache__"),
    )
    for name in ("docker-compose.yml",):
        if (repo / name).exists():
            shutil.copy2(repo / name, copy / name)
    example = (repo / "example.env").read_text(encoding="utf-8")
    (copy / "example.env").write_text(
        example.replace("\nTEST_TOKEN=\n", "\nTEST_TOKEN=testing_token\n"),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            BASH,
            str(copy / "install" / "install.sh"),
            "--backend",
            "none",
            "--dry-run",
            "--yes",
        ],
        capture_output=True,
        text=True,
        timeout=120,
        env={**os.environ, "PATH": stub_path},
        stdin=subprocess.DEVNULL,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    lines = result.stdout.splitlines()

    assert "TEST_TOKEN=" in lines
    assert "TEST_TOKEN=testing_token" not in lines
