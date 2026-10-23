"""
The installer joins NDP's NetBird network and turns Affinities on (issue #359).

Affinities is opt-in (``--affinities``); NetBird is on by default for new
installations (issue #363) and opt-in (``--netbird``) for Endpoints installed
before. Both are remembered, so a re-run keeps them. The URLs come from the
Federation configuration (sci-ndp/ndp-federation#122), not from the installer. The NetBird setup key is
read from a file or a hidden prompt and never written anywhere.

A stand-in Federation serves the configuration; ``netbird`` and ``sudo`` are
stubs, so nothing is installed and no network is joined.
"""

import json
import os
import re
import shutil
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
BASH = shutil.which("bash")

pytestmark = pytest.mark.skipif(
    BASH is None or os.name == "nt" or shutil.which("curl") is None,
    reason="needs bash and curl",
)

CONFIG_ID = "cfg359"
SETUP_KEY = "SETUP-KEY-359-never-stored"
MANAGEMENT_URL = "https://netbird.example.org"
FEDERATION_KEY = "KEY-FROM-THE-FEDERATION-361"
OWNER_TOKEN = "owner-ndp-token-361"


def _configuration(**extra):
    return {
        "_id": CONFIG_ID,
        "organization": "ORG-359",
        "ep_name": "EP-359",
        "group_name": "ndp_ep/ep-cfg359",
        **extra,
    }


@pytest.fixture
def federation():
    served = {"config": _configuration()}

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == f"/ep/{CONFIG_ID}/netbird":
                # Federation 1.12.10: only the owner's token gets the key.
                if self.headers.get("Authorization") != f"Bearer {OWNER_TOKEN}":
                    self.send_response(403)
                    self.end_headers()
                    return
                data = json.dumps(
                    {"management_url": MANAGEMENT_URL, "setup_key": FEDERATION_KEY}
                ).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
                return
            if self.path != f"/ep/{CONFIG_ID}":
                self.send_response(404)
                self.end_headers()
                return
            data = json.dumps(served["config"]).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, *args):
            pass

    server = HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    served["url"] = f"http://127.0.0.1:{server.server_address[1]}"
    yield served
    server.shutdown()


@pytest.fixture
def host(tmp_path):
    """A checkout plus stub netbird/sudo/docker that record what they are asked."""
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
        f'echo "netbird $*" >> "{log}"\n'
        'case "$1" in\n'
        "  status)\n"
        f'    if [ -f "{joined}" ]; then\n'
        f'      printf \'{{"management":{{"url":"{MANAGEMENT_URL}","connected":true}},'
        '"netbirdIp":"100.64.0.7/16"}\'\n'
        "    else\n"
        '      printf \'{"management":{"url":"","connected":false},"netbirdIp":""}\'\n'
        "    fi ;;\n"
        "  up)\n"
        "    while [ $# -gt 0 ]; do\n"
        '      [ "$1" = "--setup-key-file" ] && [ -r "$2" ] && '
        f'cp "$2" "{tmp_path}/key.seen"\n'
        "      shift\n"
        "    done\n"
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
    key_file = tmp_path / "setup-key"
    key_file.write_text(SETUP_KEY, encoding="utf-8")
    return {
        "checkout": checkout,
        "stubs": stubs,
        "log": log,
        "key": key_file,
        "tmp": tmp_path,
    }


def _install(host, federation, *args):
    return subprocess.run(
        [
            BASH,
            str(host["checkout"] / "install" / "install.sh"),
            "--config-id",
            CONFIG_ID,
            "--federation-url",
            federation["url"],
            "--backend",
            "none",
            *args,
            "--yes",
            "--no-start",
        ],
        capture_output=True,
        text=True,
        timeout=120,
        env={**os.environ, "PATH": f"{host['stubs']}{os.pathsep}{os.environ['PATH']}"},
        stdin=subprocess.DEVNULL,
    )


def _env(host):
    text = (host["checkout"] / ".env").read_text(encoding="utf-8")
    return dict(
        line.split("=", 1) for line in text.splitlines() if re.match(r"^[A-Z_]+=", line)
    )


def _netbird_calls(host):
    return host["log"].read_text(encoding="utf-8") if host["log"].exists() else ""


def test_without_the_flags_affinities_stays_off(host, federation):
    federation["config"] = _configuration(
        netbird_management_url=MANAGEMENT_URL,
        affinities_url="https://affinities.example.org",
        affinities_uid="aff-uid-1",
    )

    result = _install(host, federation, "--no-netbird")

    assert result.returncode == 0, result.stdout + result.stderr
    env = _env(host)
    assert env["NETBIRD_ENABLED"] == "False"
    assert env["AFFINITIES_ENABLED"] == "False"
    assert _netbird_calls(host) == ""


def test_netbird_joins_with_the_federation_url_and_the_key_file(host, federation):
    federation["config"] = _configuration(netbird_management_url=MANAGEMENT_URL)

    result = _install(host, federation, "--netbird-setup-key-file", str(host["key"]))

    assert result.returncode == 0, result.stdout + result.stderr
    calls = _netbird_calls(host)
    assert f"netbird up --management-url {MANAGEMENT_URL} --setup-key-file" in calls
    assert (host["tmp"] / "key.seen").read_text() == SETUP_KEY
    env = _env(host)
    assert env["NETBIRD_ENABLED"] == "True"
    assert env["NETBIRD_IP"] == "100.64.0.7"


def test_the_setup_key_is_never_written_or_printed(host, federation):
    federation["config"] = _configuration(netbird_management_url=MANAGEMENT_URL)

    result = _install(host, federation, "--netbird-setup-key-file", str(host["key"]))

    assert SETUP_KEY not in result.stdout + result.stderr
    assert SETUP_KEY not in _netbird_calls(host)
    for name in (".env", ".env.install-state"):
        assert SETUP_KEY not in (host["checkout"] / name).read_text(encoding="utf-8")


def test_a_re_run_keeps_netbird_without_the_key(host, federation):
    federation["config"] = _configuration(netbird_management_url=MANAGEMENT_URL)
    _install(host, federation, "--netbird-setup-key-file", str(host["key"]))
    host["log"].unlink()

    result = _install(host, federation)

    assert result.returncode == 0, result.stdout + result.stderr
    assert "netbird up" not in _netbird_calls(host)
    assert _env(host)["NETBIRD_ENABLED"] == "True"
    assert _env(host)["NETBIRD_IP"] == "100.64.0.7"


def test_the_management_url_can_be_overridden(host, federation):
    federation["config"] = _configuration(netbird_management_url=MANAGEMENT_URL)

    _install(
        host,
        federation,
        "--netbird-setup-key-file",
        str(host["key"]),
        "--netbird-management-url",
        "https://other.example.org",
    )

    assert "--management-url https://other.example.org" in _netbird_calls(host)


def test_netbird_without_a_management_url_stops(host, federation):
    result = _install(host, federation, "--netbird-setup-key-file", str(host["key"]))

    assert result.returncode == 1
    assert "needs the NetBird management URL" in result.stderr


def test_netbird_without_a_key_stops_when_not_connected(host, federation):
    federation["config"] = _configuration(netbird_management_url=MANAGEMENT_URL)

    result = _install(host, federation, "--netbird")

    assert result.returncode == 1
    assert "--ndp-token-file" in result.stderr


def test_affinities_is_turned_on_from_the_configuration(host, federation):
    federation["config"] = _configuration(
        affinities_url="https://affinities.example.org", affinities_uid="aff-uid-1"
    )

    result = _install(host, federation, "--affinities")

    assert result.returncode == 0, result.stdout + result.stderr
    env = _env(host)
    assert env["AFFINITIES_ENABLED"] == "True"
    assert env["AFFINITIES_URL"] == "https://affinities.example.org"
    assert env["AFFINITIES_EP_UUID"] == "aff-uid-1"

    again = _install(host, federation)
    assert again.returncode == 0, again.stdout + again.stderr
    assert _env(host)["AFFINITIES_ENABLED"] == "True"


def test_affinities_without_an_id_stops(host, federation):
    federation["config"] = _configuration(
        affinities_url="https://affinities.example.org"
    )

    result = _install(host, federation, "--affinities")

    assert result.returncode == 1
    assert "--affinities needs a Federation registration" in result.stderr


def test_the_key_comes_from_the_federation_with_the_owners_token(host, federation):
    """Issue #361: the person installing never sees the key."""
    federation["config"] = _configuration(netbird_management_url=MANAGEMENT_URL)
    token_file = host["tmp"] / "ndp-token"
    token_file.write_text(OWNER_TOKEN + "\n", encoding="utf-8")

    result = _install(
        host, federation, "--netbird", "--ndp-token-file", str(token_file)
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert (host["tmp"] / "key.seen").read_text() == FEDERATION_KEY
    assert _env(host)["NETBIRD_ENABLED"] == "True"
    for secret in (FEDERATION_KEY, OWNER_TOKEN):
        assert secret not in result.stdout + result.stderr
        assert secret not in _netbird_calls(host)
        for name in (".env", ".env.install-state"):
            text = (host["checkout"] / name).read_text(encoding="utf-8")
            assert secret not in text


def test_a_token_that_does_not_own_the_configuration_stops(host, federation):
    federation["config"] = _configuration(netbird_management_url=MANAGEMENT_URL)
    token_file = host["tmp"] / "ndp-token"
    token_file.write_text("someone-elses-token", encoding="utf-8")

    result = _install(
        host, federation, "--netbird", "--ndp-token-file", str(token_file)
    )

    assert result.returncode == 1
    assert "does not own configuration" in result.stderr
    assert "netbird up" not in _netbird_calls(host)


# ---------------------------------------------------------------------------
# NetBird by default on new installations (issue #363)
# ---------------------------------------------------------------------------
# A new installation joins without --netbird; it never stops because of
# NetBird. An Endpoint installed earlier, re-run to upgrade, keeps what it had.


def _token_file(host, token=OWNER_TOKEN):
    token_file = host["tmp"] / "ndp-token"
    token_file.write_text(token, encoding="utf-8")
    return str(token_file)


def _state(host):
    path = host["checkout"] / ".env.install-state"
    if not path.exists():
        return {}
    return dict(
        line.split("=", 1)
        for line in path.read_text(encoding="utf-8").splitlines()
        if "=" in line
    )


def test_a_new_installation_joins_netbird_by_default(host, federation):
    federation["config"] = _configuration(netbird_management_url=MANAGEMENT_URL)

    result = _install(host, federation, "--ndp-token-file", _token_file(host))

    assert result.returncode == 0, result.stdout + result.stderr
    assert f"netbird up --management-url {MANAGEMENT_URL}" in _netbird_calls(
        host
    ), result.stderr
    assert (host["tmp"] / "key.seen").read_text() == FEDERATION_KEY
    assert _env(host)["NETBIRD_ENABLED"] == "True"
    assert _state(host)["NETBIRD"] == "yes"


def test_by_default_a_missing_key_does_not_stop_the_installation(host, federation):
    federation["config"] = _configuration(netbird_management_url=MANAGEMENT_URL)

    result = _install(host, federation)

    assert result.returncode == 0, result.stdout + result.stderr
    assert "netbird up" not in _netbird_calls(host)
    assert _env(host)["NETBIRD_ENABLED"] == "False"
    assert "did not join NetBird" in result.stderr
    assert "--ndp-token-file" in result.stderr


def test_by_default_a_refused_key_does_not_stop_the_installation(host, federation):
    federation["config"] = _configuration(netbird_management_url=MANAGEMENT_URL)

    result = _install(
        host, federation, "--ndp-token-file", _token_file(host, "someone-elses-token")
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "does not own configuration" in result.stderr
    assert "netbird up" not in _netbird_calls(host)
    assert _env(host)["NETBIRD_ENABLED"] == "False"


def test_by_default_no_management_url_installs_without_netbird(host, federation):
    result = _install(host, federation, "--ndp-token-file", _token_file(host))

    assert result.returncode == 0, result.stdout + result.stderr
    assert "netbird up" not in _netbird_calls(host)
    assert _env(host)["NETBIRD_ENABLED"] == "False"


def test_a_failed_default_join_is_tried_again_on_the_next_run(host, federation):
    federation["config"] = _configuration(netbird_management_url=MANAGEMENT_URL)
    _install(host, federation)

    result = _install(host, federation, "--ndp-token-file", _token_file(host))

    assert result.returncode == 0, result.stdout + result.stderr
    assert f"netbird up --management-url {MANAGEMENT_URL}" in _netbird_calls(host)
    assert _env(host)["NETBIRD_ENABLED"] == "True"


def test_no_netbird_turns_it_off_and_is_remembered(host, federation):
    federation["config"] = _configuration(netbird_management_url=MANAGEMENT_URL)
    token = _token_file(host)

    first = _install(host, federation, "--no-netbird", "--ndp-token-file", token)
    again = _install(host, federation, "--ndp-token-file", token)

    assert first.returncode == 0, first.stdout + first.stderr
    assert again.returncode == 0, again.stdout + again.stderr
    assert _netbird_calls(host) == ""
    assert _env(host)["NETBIRD_ENABLED"] == "False"
    assert _state(host)["NETBIRD"] == "no"


def test_an_endpoint_installed_before_is_not_joined_on_upgrade(host, federation):
    """Installed before NetBird existed in the installer: nothing recorded."""
    federation["config"] = _configuration(netbird_management_url=MANAGEMENT_URL)
    _install(host, federation, "--no-netbird")
    state = host["checkout"] / ".env.install-state"
    state.write_text(
        "".join(
            line + "\n"
            for line in state.read_text(encoding="utf-8").splitlines()
            if not line.startswith("NETBIRD=")
        ),
        encoding="utf-8",
    )

    result = _install(host, federation, "--ndp-token-file", _token_file(host))

    assert result.returncode == 0, result.stdout + result.stderr
    assert _netbird_calls(host) == ""
    assert _env(host)["NETBIRD_ENABLED"] == "False"


def test_explicit_netbird_still_stops_without_a_key(host, federation):
    federation["config"] = _configuration(netbird_management_url=MANAGEMENT_URL)

    result = _install(host, federation, "--netbird")

    assert result.returncode == 1
    assert "--ndp-token-file" in result.stderr


def test_by_default_without_passwordless_sudo_it_carries_on(host, federation):
    federation["config"] = _configuration(netbird_management_url=MANAGEMENT_URL)
    # sudo that would need a password: -n refuses.
    (host["stubs"] / "sudo").write_text(
        '#!/bin/sh\n[ "$1" = "-n" ] && exit 1\nexec "$@"\n', encoding="utf-8"
    )

    result = _install(host, federation, "--ndp-token-file", _token_file(host))

    assert result.returncode == 0, result.stdout + result.stderr
    assert "needs sudo" in result.stderr
    assert "netbird up" not in _netbird_calls(host)
    assert _env(host)["NETBIRD_ENABLED"] == "False"


def test_an_unattended_run_on_a_connected_machine_records_netbird(host, federation):
    """Issue #367: seeing an existing connection needs no sudo."""
    federation["config"] = _configuration(netbird_management_url=MANAGEMENT_URL)
    # Already connected, as the second Endpoint on a host that joined before.
    (host["tmp"] / "netbird.joined").touch()
    # sudo that would need a password: -n refuses, anything else fails too.
    (host["stubs"] / "sudo").write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")

    result = _install(host, federation)

    assert result.returncode == 0, result.stdout + result.stderr
    assert "needs sudo" not in result.stderr
    assert "netbird up" not in _netbird_calls(host)
    assert _env(host)["NETBIRD_ENABLED"] == "True"
    assert _env(host)["NETBIRD_IP"] == "100.64.0.7"
    assert _state(host)["NETBIRD"] == "yes"


# The NetBird client is installed from a pinned release whose checksum the
# installer carries (install/netbird.sha256), not by piping NetBird's install
# script into a root shell (issue #375). A local "release" stands in for
# GitHub: a tarball holding the stub client.


def _arch():
    machine = os.uname().machine
    return {"x86_64": "amd64", "amd64": "amd64", "aarch64": "arm64"}.get(machine)


@pytest.fixture
def no_client(host):
    """The host without a NetBird client, and a release of the stub one."""
    import hashlib
    import tarfile

    pinned = (host["checkout"] / "install" / "netbird.sha256").read_text()
    version = re.search(r"netbird_([0-9.]+)_linux_", pinned).group(1)
    name = f"netbird_{version}_linux_{_arch()}.tar.gz"
    releases = host["tmp"] / "releases"
    (releases / f"v{version}").mkdir(parents=True)
    tarball = releases / f"v{version}" / name
    with tarfile.open(tarball, "w:gz") as archive:
        archive.add(host["stubs"] / "netbird", arcname="netbird")
    (host["stubs"] / "netbird").unlink()
    bin_dir = host["tmp"] / "installed-bin"
    bin_dir.mkdir()
    return {
        **host,
        "releases": releases,
        "bin_dir": bin_dir,
        "tarball": tarball,
        "sha": hashlib.sha256(tarball.read_bytes()).hexdigest(),
        "name": name,
        "pinned": pinned,
    }


def _pin(no_client, sha):
    lines = [
        f"{sha}  {no_client['name']}" if no_client["name"] in line else line
        for line in no_client["pinned"].splitlines()
    ]
    (no_client["checkout"] / "install" / "netbird.sha256").write_text(
        "\n".join(lines) + "\n"
    )


def _install_fresh(no_client, federation):
    path = os.pathsep.join(
        [str(no_client["stubs"]), str(no_client["bin_dir"]), os.environ["PATH"]]
    )
    return subprocess.run(
        [
            BASH,
            str(no_client["checkout"] / "install" / "install.sh"),
            "--config-id",
            CONFIG_ID,
            "--federation-url",
            federation["url"],
            "--backend",
            "none",
            "--netbird-setup-key-file",
            str(no_client["key"]),
            "--yes",
            "--no-start",
        ],
        capture_output=True,
        text=True,
        timeout=120,
        env={
            **os.environ,
            "PATH": path,
            "EP_NETBIRD_RELEASES_URL": f"file://{no_client['releases']}",
            "EP_NETBIRD_BIN_DIR": str(no_client["bin_dir"]),
        },
        stdin=subprocess.DEVNULL,
    )


@pytest.mark.skipif(_arch() is None, reason="NetBird ships linux amd64/arm64 only")
def test_the_client_is_installed_from_the_pinned_release(no_client, federation):
    federation["config"] = _configuration(netbird_management_url=MANAGEMENT_URL)
    _pin(no_client, no_client["sha"])

    result = _install_fresh(no_client, federation)

    assert result.returncode == 0, result.stdout + result.stderr
    assert (no_client["bin_dir"] / "netbird").exists()
    calls = _netbird_calls(no_client)
    assert "netbird service install" in calls
    assert "netbird service start" in calls
    assert f"netbird up --management-url {MANAGEMENT_URL}" in calls
    assert "sha256 verified" in result.stdout


@pytest.mark.skipif(_arch() is None, reason="NetBird ships linux amd64/arm64 only")
def test_a_client_that_does_not_match_the_checksum_is_not_installed(
    no_client, federation
):
    federation["config"] = _configuration(netbird_management_url=MANAGEMENT_URL)
    _pin(no_client, "0" * 64)

    result = _install_fresh(no_client, federation)

    assert result.returncode != 0
    assert not (no_client["bin_dir"] / "netbird").exists()
    assert "checksum" in result.stderr
    assert _netbird_calls(no_client) == ""


def test_the_install_script_is_no_longer_piped_into_a_shell():
    body = (REPO / "install" / "install.sh").read_text(encoding="utf-8")

    assert "pkgs.netbird.io/install.sh" not in body


def test_the_pinned_checksums_are_well_formed():
    pinned = (REPO / "install" / "netbird.sha256").read_text(encoding="utf-8")
    entries = [line for line in pinned.splitlines() if line and line[0] != "#"]

    assert len(entries) == 2
    for line in entries:
        assert re.fullmatch(
            r"[0-9a-f]{64}  netbird_[0-9]+\.[0-9]+\.[0-9]+_linux_(amd64|arm64)\.tar\.gz",
            line,
        )
