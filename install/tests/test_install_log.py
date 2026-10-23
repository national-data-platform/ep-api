"""
Every installer run leaves a log behind (issue #374).

Before, everything went to the terminal only: a run that failed ten minutes in,
unattended, left nothing on the machine to say where it stopped. Now the whole
run is appended to ``install.log`` next to the checkout (or to ``--log-file``),
with a header saying which installer ran, with which arguments and against
which Federation, and a failure names the log.

Each run is stopped at the prerequisite check by a ``docker`` that refuses to
answer, which is enough to see the header, the output and the failure land in
the file.
"""

import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
BASH = shutil.which("bash")

pytestmark = pytest.mark.skipif(BASH is None or os.name == "nt", reason="needs bash")

ANSI = re.compile(r"\x1b\[[0-9;]*m")


@pytest.fixture
def checkout(tmp_path):
    """A checkout of the installer plus a docker that never answers."""
    root = tmp_path / "ep-api"
    shutil.copytree(REPO / "install", root / "install")
    shutil.copy(REPO / "example.env", root / "example.env")
    shutil.copy(REPO / "docker-compose.yml", root / "docker-compose.yml")
    stubs = tmp_path / "bin"
    stubs.mkdir()
    (stubs / "docker").write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
    (stubs / "docker").chmod(0o755)
    return {"root": root, "stubs": stubs, "tmp": tmp_path}


def _run(checkout, *args):
    return subprocess.run(
        [BASH, str(checkout["root"] / "install" / "install.sh"), *args, "--dry-run"],
        capture_output=True,
        text=True,
        timeout=120,
        env={
            **os.environ,
            "PATH": f"{checkout['stubs']}{os.pathsep}{os.environ['PATH']}",
        },
        stdin=subprocess.DEVNULL,
    )


def test_a_run_is_logged_next_to_the_checkout(checkout):
    result = _run(checkout, "--config-id", "FAKE", "--env", "test")

    log = checkout["root"] / "install.log"
    assert result.returncode != 0
    assert log.exists(), result.stdout + result.stderr
    text = log.read_text(encoding="utf-8")
    assert "Federation: https://federation.ndp.utah.edu/test" in text


def test_the_header_says_what_ran(checkout):
    _run(checkout, "--config-id", "FAKE", "--env", "test")

    text = (checkout["root"] / "install.log").read_text(encoding="utf-8")
    assert "install.sh run" in text
    assert "args: --config-id FAKE --env test --dry-run" in text
    assert "federation: https://federation.ndp.utah.edu/test" in text
    assert "version:" in text
    assert "user:" in text


def test_the_failure_lands_in_the_log_and_names_it(checkout):
    result = _run(checkout, "--config-id", "FAKE")

    log = checkout["root"] / "install.log"
    assert f"install log: {log}" in result.stderr
    text = log.read_text(encoding="utf-8")
    assert "[fail]" in text


def test_the_log_has_no_colour_codes(checkout):
    _run(checkout, "--config-id", "FAKE")

    text = (checkout["root"] / "install.log").read_text(encoding="utf-8")
    assert not ANSI.search(text)


def test_a_rerun_appends_rather_than_truncates(checkout):
    _run(checkout, "--config-id", "FIRST")
    _run(checkout, "--config-id", "SECOND")

    text = (checkout["root"] / "install.log").read_text(encoding="utf-8")
    assert "--config-id FIRST" in text
    assert "--config-id SECOND" in text
    assert text.count("install.sh run") == 2


def test_secrets_given_as_arguments_are_not_logged(checkout):
    _run(
        checkout,
        "--backend",
        "ckan",
        "--ckan-password",
        "pw-Zq81",
        "--ckan-api-key",
        "ak-Zq82",
        "--s3-endpoint",
        "s3.example.invalid",
        "--s3-access-key",
        "ac-Zq83",
        "--s3-secret-key",
        "sk-Zq84",
    )

    text = (checkout["root"] / "install.log").read_text(encoding="utf-8")
    for secret in ("pw-Zq81", "ak-Zq82", "ac-Zq83", "sk-Zq84"):
        assert secret not in text
    assert "--ckan-password ***" in text


def test_the_log_is_readable_by_its_owner_only(checkout):
    _run(checkout, "--config-id", "FAKE")

    mode = (checkout["root"] / "install.log").stat().st_mode & 0o777
    assert mode == 0o600


def test_log_file_chooses_where_it_goes(checkout):
    chosen = checkout["tmp"] / "elsewhere" / "run.log"
    chosen.parent.mkdir()

    result = _run(checkout, "--config-id", "FAKE", "--log-file", str(chosen))

    assert chosen.exists()
    assert "Federation:" in chosen.read_text(encoding="utf-8")
    assert not (checkout["root"] / "install.log").exists()
    assert f"install log: {chosen}" in result.stderr


def test_dev_null_turns_the_log_off(checkout):
    result = _run(checkout, "--config-id", "FAKE", "--log-file", "/dev/null")

    assert not (checkout["root"] / "install.log").exists()
    assert "install log:" not in result.stderr
    assert "Federation:" in result.stdout


def test_terminal_output_is_unchanged(checkout):
    """The log is a copy: what the operator sees still arrives, on both streams."""
    result = _run(checkout, "--config-id", "FAKE", "--env", "test")

    assert "Federation: https://federation.ndp.utah.edu/test" in result.stdout
    assert "[fail]" in result.stderr


def test_an_unwritable_log_does_not_stop_the_install(checkout):
    blocked = checkout["tmp"] / "no-such-dir" / "run.log"

    result = _run(checkout, "--config-id", "FAKE", "--log-file", str(blocked))

    assert "Cannot write the install log" in result.stderr
    assert "Federation:" in result.stdout
