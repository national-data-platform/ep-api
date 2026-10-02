"""
The installer sandbox has to run on the platform it is most needed on.

`sandbox.sh` is the only way to exercise the installer without a spare
machine, and it failed on Windows with an error naming a path nobody wrote:
Git Bash rewrites arguments that look like absolute POSIX paths into Windows
ones before handing them to `docker exec`, so the container was asked for
`C:/Program Files/Git/opt/ep-api/install/install.sh` (issue #291).

Running the sandbox here would need a Docker daemon, so this pins the guard
rather than the behaviour. That is worth doing anyway: the guard is one line
whose absence breaks nothing visible on Linux, which is exactly the kind of
line that gets tidied away.
"""

from pathlib import Path

SANDBOX = Path(__file__).resolve().parents[1] / "tests" / "sandbox.sh"


def test_the_sandbox_script_exists():
    assert SANDBOX.is_file()


def test_path_conversion_is_disabled():
    """Without this the sandbox cannot run from Git Bash at all."""
    assert "MSYS_NO_PATHCONV=1" in SANDBOX.read_text(encoding="utf-8")


def test_the_guard_is_exported_before_the_first_docker_call():
    """
    An export after the first `docker exec` would protect nothing: the
    rewrite happens when the argument is handed over, not when it is read.

    Comments are skipped: the usage header shows a `docker exec` the reader
    is meant to type, which is not a call this script makes.
    """
    lines = SANDBOX.read_text(encoding="utf-8").splitlines()

    def first(needle):
        for number, line in enumerate(lines):
            if line.lstrip().startswith("#"):
                continue
            if needle in line:
                return number
        raise AssertionError("not found outside comments: " + needle)

    assert first("MSYS_NO_PATHCONV") < first("docker exec")


def test_the_guard_says_why_it_is_there():
    """It is inert on Linux, so the reason has to travel with it."""
    body = SANDBOX.read_text(encoding="utf-8")
    guard = body[: body.index("MSYS_NO_PATHCONV=1")]

    assert "Git Bash" in guard or "MSYS" in guard
