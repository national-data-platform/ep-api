"""
In an interactive run, the catalog question offers what --backend chose (#366).

The question "Which local catalog should this Endpoint use?" always offered
1 (None) as its default, so an operator who ran `install.sh --backend mongodb`
in a terminal and pressed Enter got no catalog. The default now follows
`--backend` (and `--mongodb-url` / `--ckan-url` for an existing one).

The prompts only appear on a terminal, so the installer runs under a
pseudo-terminal, with every question answered by pressing Enter (except the
offer to register with the Federation, answered no).
"""

import os
import pty
import select
import shutil
import subprocess
import time
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
BASH = shutil.which("bash")

pytestmark = pytest.mark.skipif(
    BASH is None or os.name == "nt",
    reason="needs bash and a pseudo-terminal",
)


@pytest.fixture
def checkout(tmp_path):
    copy = tmp_path / "ep-api"
    shutil.copytree(REPO / "install", copy / "install")
    shutil.copy(REPO / "example.env", copy / "example.env")
    stubs = tmp_path / "bin"
    stubs.mkdir()
    for name, body in (("docker", "exit 0"), ("curl", "printf 000\nexit 7")):
        (stubs / name).write_text(f"#!/bin/sh\n{body}\n", encoding="utf-8")
        (stubs / name).chmod(0o755)
    return copy, stubs


def _run_pressing_enter(checkout, *args):
    copy, stubs = checkout
    env = {
        **os.environ,
        "PATH": f"{stubs}{os.pathsep}{os.environ['PATH']}",
        "TERM": "dumb",
    }
    main, child = pty.openpty()
    process = subprocess.Popen(
        [BASH, str(copy / "install" / "install.sh"), "--dry-run", *args],
        stdin=child,
        stdout=child,
        stderr=child,
        env=env,
        cwd=copy,
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
            last = pending.rstrip(" ").splitlines()[-1] if pending.strip() else ""
            if last.endswith(":"):
                # Enter everywhere, except: do not register with the real
                # Federation.
                answer = b"n\n" if "Register this Endpoint" in last else b"\n"
                os.write(main, answer)
                pending = ""
        elif process.poll() is not None:
            break
    try:
        process.wait(timeout=30)
    except subprocess.TimeoutExpired:
        # Show where the installer stopped instead of only the timeout
        # (issue #404).
        process.kill()
        os.close(main)
        pytest.fail(
            "install.sh did not finish; it was waiting after:\n" + output[-2000:]
        )
    os.close(main)
    lines = [line.strip() for line in output.splitlines()]
    return process.returncode, output, lines


@pytest.mark.parametrize(
    "args, choice, backend",
    [
        (("--backend", "mongodb"), "2", "mongodb"),
        (("--backend", "ckan"), "4", "ckan"),
        (
            ("--backend", "mongodb", "--mongodb-url", "mongodb://db.example:27017"),
            "3",
            "mongodb",
        ),
        ((), "1", "none"),
    ],
)
def test_enter_keeps_the_backend_given_on_the_command_line(
    checkout, args, choice, backend
):
    code, output, lines = _run_pressing_enter(checkout, *args)

    assert f"Choice [{choice}]:" in output, output
    assert f"LOCAL_CATALOG_BACKEND={backend}" in lines, output
    assert code == 0, output


def test_an_existing_mongodb_url_is_offered_as_its_default(checkout):
    url = "mongodb://db.example:27017"
    code, output, lines = _run_pressing_enter(
        checkout, "--backend", "mongodb", "--mongodb-url", url
    )

    assert f"[{url}]:" in output, output
    assert code == 0, output


SLOW_TEE = """#!/usr/bin/env python3
# A tee that is slow to copy, like one on a loaded machine (issue #404).
import os, sys, time
append = "-a" in sys.argv[1:]
files = [open(a, "ab" if append else "wb") for a in sys.argv[1:] if a != "-a"]
while True:
    chunk = os.read(0, 4096)
    if not chunk:
        break
    time.sleep(0.05)
    os.write(1, chunk)
    for f in files:
        f.write(chunk)
        f.flush()
"""


def test_each_prompt_comes_after_its_explanation_when_the_log_is_slow(checkout):
    """The install log copies stdout and stderr through separate tee processes;
    a prompt must still follow the text that explains it (issue #404)."""
    copy, stubs = checkout
    (stubs / "tee").write_text(SLOW_TEE, encoding="utf-8")
    (stubs / "tee").chmod(0o755)

    code, output, lines = _run_pressing_enter(checkout, "--backend", "mongodb")

    assert code == 0, output
    explanation = output.index("Leave blank and the next step offers to register now.")
    assert output.index("Configuration id (blank to skip):") > explanation, output
    options = output.index("5) CKAN, one I already have")
    assert output.index("Choice [2]:") > options, output
