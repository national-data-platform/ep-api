"""
NetBird joins when the person installing has a directory account (issue #369).

NetBird's CLI resolves the sudo invoking user (``SUDO_USER``) by reading local
accounts only, and refuses to go on when it cannot, so on a host whose users
come from LDAP/SSSD (not in ``/etc/passwd``) ``sudo netbird up`` failed with
"resolve sudo invoking user …: refusing to fall back to root". The installer
now runs ``netbird up`` without the sudo user variables in that case.

The stub ``netbird`` behaves like the real one: ``up`` fails while
``SUDO_USER`` names an account missing from ``/etc/passwd``.
"""

import os
import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
BASH = shutil.which("bash")
MANAGEMENT_URL = "https://netbird.example.org"
DIRECTORY_USER = "u6061931-directory"

pytestmark = pytest.mark.skipif(
    BASH is None or os.name == "nt",
    reason="needs bash; the stubs are POSIX shell scripts",
)


@pytest.fixture
def host(tmp_path):
    checkout = tmp_path / "ep-api"
    shutil.copytree(REPO / "install", checkout / "install")
    shutil.copy(REPO / "example.env", checkout / "example.env")
    shutil.copy(REPO / "docker-compose.yml", checkout / "docker-compose.yml")
    stubs = tmp_path / "bin"
    stubs.mkdir()
    log = tmp_path / "netbird.log"
    joined = tmp_path / "netbird.joined"
    (stubs / "netbird").write_text(
        "#!/bin/sh\n"
        f'echo "netbird $* SUDO_USER=${{SUDO_USER:-}}" >> "{log}"\n'
        'case "$1" in\n'
        "  status)\n"
        f'    if [ -f "{joined}" ]; then\n'
        f'      printf \'{{"management":{{"url":"{MANAGEMENT_URL}","connected":true}},'
        '"netbirdIp":"100.64.0.9/16"}\'\n'
        "    else\n"
        '      printf \'{"management":{"url":"","connected":false},"netbirdIp":""}\'\n'
        "    fi ;;\n"
        "  up)\n"
        '    if [ -n "${SUDO_USER:-}" ] && ! grep -q "^${SUDO_USER}:" /etc/passwd; then\n'
        '      echo "Error: get current user: resolve sudo invoking user \\"$SUDO_USER\\":'
        ' refusing to fall back to root" >&2\n'
        "      exit 1\n"
        "    fi\n"
        f'    touch "{joined}" ;;\n'
        "esac\n",
        encoding="utf-8",
    )
    (stubs / "sudo").write_text(
        '#!/bin/sh\n[ "$1" = "-n" ] && shift\nexec "$@"\n', encoding="utf-8"
    )
    (stubs / "docker").write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    for stub in stubs.iterdir():
        stub.chmod(0o755)
    key = tmp_path / "setup-key"
    key.write_text("NB-SETUP-KEY", encoding="utf-8")
    return {"checkout": checkout, "stubs": stubs, "log": log, "key": key}


def _install(host, sudo_user):
    env = {**os.environ, "PATH": f"{host['stubs']}{os.pathsep}{os.environ['PATH']}"}
    env.pop("SUDO_UID", None)
    env.pop("SUDO_GID", None)
    if sudo_user:
        env["SUDO_USER"] = sudo_user
    else:
        env.pop("SUDO_USER", None)
    return subprocess.run(
        [
            BASH,
            str(host["checkout"] / "install" / "install.sh"),
            "--backend",
            "none",
            "--netbird",
            "--netbird-management-url",
            MANAGEMENT_URL,
            "--netbird-setup-key-file",
            str(host["key"]),
            "--yes",
            "--no-start",
        ],
        capture_output=True,
        text=True,
        timeout=120,
        env=env,
        stdin=subprocess.DEVNULL,
    )


def _up_calls(host):
    text = host["log"].read_text(encoding="utf-8") if host["log"].exists() else ""
    return [line for line in text.splitlines() if line.startswith("netbird up ")]


def test_a_directory_account_joins(host):
    """Run through sudo by an account that is not in /etc/passwd."""
    result = _install(host, DIRECTORY_USER)

    assert result.returncode == 0, result.stdout + result.stderr
    assert "refusing to fall back to root" not in result.stderr
    assert "Joined NetBird" in result.stdout
    assert all(call.endswith("SUDO_USER=") for call in _up_calls(host))


def test_a_local_account_keeps_the_sudo_user(host):
    """Nothing changes for an account NetBird can resolve."""
    local_user = (
        Path("/etc/passwd").read_text(encoding="utf-8").splitlines()[0].split(":")[0]
    )

    result = _install(host, local_user)

    assert result.returncode == 0, result.stdout + result.stderr
    assert _up_calls(host)
    assert all(call.endswith(f"SUDO_USER={local_user}") for call in _up_calls(host))
