"""
``status``, ``stop``, ``start`` and ``uninstall`` (issue #372).

The installer could only install. Stopping an Endpoint meant guessing its
Compose project and port, removing one was a manual hunt through containers,
volumes and ``.env.backup.*`` files (which hold credentials), and support could
not ask "what is running here?" without reading ``.env`` by hand.

The subcommands act on the Endpoint the checkout already holds, through the
Compose project's labels, so no port or profile has to be remembered. Data is
only removed with ``uninstall --remove-data``.

``docker`` is a stub that answers from files and logs what it is asked.
"""

import os
import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
BASH = shutil.which("bash")

pytestmark = pytest.mark.skipif(
    BASH is None or os.name == "nt" or shutil.which("curl") is None,
    reason="needs bash and curl",
)


@pytest.fixture
def endpoint(tmp_path):
    """An installed checkout and a docker that knows its containers."""
    root = tmp_path / "ndp-ep"
    shutil.copytree(REPO / "install", root / "install")
    shutil.copy(REPO / "example.env", root / "example.env")
    shutil.copy(REPO / "docker-compose.yml", root / "docker-compose.yml")
    (root / ".env").write_text(
        "LOCAL_CATALOG_BACKEND=mongodb\nROOT_PATH=\nS3_SECRET_KEY=secret-xyz\n",
        encoding="utf-8",
    )
    (root / ".env.install-state").write_text(
        "EP_INSTANCE=ndp\nINSTALLER_VERSION=v0.34.62\nNETBIRD=yes\nEP_API_PORT=8099\n",
        encoding="utf-8",
    )
    (root / ".env.backup.20261001-101010").write_text("OLD=1\n", encoding="utf-8")
    stubs = tmp_path / "bin"
    stubs.mkdir()
    for name, content in {
        "running.txt": "c1\nc2\n",
        "all.txt": "c1\nc2\n",
        "volumes.txt": "ndp-ep_mongodb_data\n",
        "networks.txt": "ndp-ep_ndp-network\n",
    }.items():
        (tmp_path / name).write_text(content, encoding="utf-8")
    log = tmp_path / "docker.log"
    (stubs / "docker").write_text(
        "#!/bin/sh\n"
        f'echo "docker $*" >> "{log}"\n'
        f'T="{tmp_path}"\n'
        'case "$1" in\n'
        '  ps) case " $* " in *" -a "*|*" -aq "*) cat "$T/all.txt" ;; *) cat "$T/running.txt" ;; esac ;;\n'
        '  volume) [ "$2" = ls ] && cat "$T/volumes.txt" ;;\n'
        '  network) [ "$2" = ls ] && cat "$T/networks.txt" ;;\n'
        "  port) echo 0.0.0.0:8099 ;;\n"
        "esac\n"
        "exit 0\n",
        encoding="utf-8",
    )
    (stubs / "netbird").write_text(
        "#!/bin/sh\n"
        'printf \'{"management":{"url":"https://nb.example.org","connected":true},'
        '"netbirdIp":"100.64.0.9/16"}\'\n',
        encoding="utf-8",
    )
    for stub in stubs.iterdir():
        stub.chmod(0o755)
    return {"root": root, "stubs": stubs, "log": log, "tmp": tmp_path}


def _run(endpoint, *args, script=None):
    return subprocess.run(
        [BASH, str(script or endpoint["root"] / "install" / "install.sh"), *args],
        capture_output=True,
        text=True,
        timeout=120,
        env={
            **os.environ,
            "PATH": f"{endpoint['stubs']}{os.pathsep}{os.environ['PATH']}",
            "EP_INSTALL_DIR": str(endpoint["root"]),
        },
        stdin=subprocess.DEVNULL,
    )


def _calls(endpoint):
    return endpoint["log"].read_text() if endpoint["log"].exists() else ""


class TestStatus:
    def test_it_reports_what_is_installed(self, endpoint):
        result = _run(endpoint, "status")

        assert result.returncode == 0, result.stdout + result.stderr
        out = result.stdout
        assert "instance: ndp" in out
        assert "compose project: ndp-ep" in out
        assert "version: v0.34.62" in out
        assert "catalog: mongodb" in out
        assert "containers: 2 running of 2" in out
        assert "port: 8099" in out
        assert "NetBird: connected (100.64.0.9)" in out

    def test_it_says_when_the_endpoint_does_not_answer(self, endpoint):
        result = _run(endpoint, "status")

        assert "health: not answering at http://localhost:8099/health" in result.stdout

    def test_it_changes_nothing(self, endpoint):
        _run(endpoint, "status")

        calls = _calls(endpoint)
        for action in (
            "docker stop",
            "docker start",
            "docker rm",
            "docker volume rm",
            "docker network rm",
            "compose up",
            "compose down",
        ):
            assert action not in calls

    def test_it_never_prints_secrets(self, endpoint):
        result = _run(endpoint, "status")

        assert "secret-xyz" not in result.stdout + result.stderr

    def test_it_does_not_install_anything(self, endpoint):
        result = _run(endpoint, "status")

        assert "Checking prerequisites" not in result.stdout
        assert "Rendering .env" not in result.stdout


class TestStopAndStart:
    def test_stop_stops_the_projects_containers(self, endpoint):
        result = _run(endpoint, "stop")

        assert result.returncode == 0, result.stdout + result.stderr
        calls = _calls(endpoint)
        assert "label=com.docker.compose.project=ndp-ep" in calls
        assert "docker stop c1 c2" in calls

    def test_stop_when_nothing_runs(self, endpoint):
        (endpoint["tmp"] / "running.txt").write_text("")

        result = _run(endpoint, "stop")

        assert result.returncode == 0
        assert "already stopped" in result.stdout
        assert "docker stop" not in _calls(endpoint)

    def test_start_starts_the_same_containers(self, endpoint):
        """Started as they were created, so the port stays (issue #370)."""
        result = _run(endpoint, "start")

        calls = _calls(endpoint)
        assert "docker start c1 c2" in calls
        assert "compose up" not in calls
        assert "8099" in result.stdout + result.stderr

    def test_start_without_containers_points_at_the_installer(self, endpoint):
        (endpoint["tmp"] / "all.txt").write_text("")

        result = _run(endpoint, "start")

        assert result.returncode != 0
        assert "run the installer" in result.stderr


class TestUninstall:
    def test_it_needs_confirmation(self, endpoint):
        result = _run(endpoint, "uninstall")

        assert result.returncode != 0
        assert "--yes" in result.stderr
        assert "docker rm" not in _calls(endpoint)

    def test_it_removes_containers_and_networks_but_keeps_data(self, endpoint):
        result = _run(endpoint, "uninstall", "--yes")

        assert result.returncode == 0, result.stdout + result.stderr
        calls = _calls(endpoint)
        assert "docker rm -f c1 c2" in calls
        assert "docker network rm ndp-ep_ndp-network" in calls
        assert "docker volume rm" not in calls
        assert "kept" in result.stdout

    def test_it_removes_the_env_backups_that_hold_old_secrets(self, endpoint):
        _run(endpoint, "uninstall", "--yes")

        assert not list(endpoint["root"].glob(".env.backup.*"))

    def test_without_remove_data_what_opens_the_data_stays(self, endpoint):
        """The install state holds the generated passwords the data needs."""
        _run(endpoint, "uninstall", "--yes")

        assert (endpoint["root"] / ".env.install-state").exists()
        assert (endpoint["root"] / ".env").exists()

    def test_remove_data_removes_volumes_and_credentials(self, endpoint):
        result = _run(endpoint, "uninstall", "--remove-data", "--yes")

        assert result.returncode == 0, result.stdout + result.stderr
        assert "docker volume rm ndp-ep_mongodb_data" in _calls(endpoint)
        assert not (endpoint["root"] / ".env.install-state").exists()
        assert not (endpoint["root"] / ".env").exists()

    def test_netbird_is_left_and_how_to_leave_is_said(self, endpoint):
        result = _run(endpoint, "uninstall", "--yes")

        assert "netbird down" in result.stdout

    def test_the_checkout_itself_is_left(self, endpoint):
        _run(endpoint, "uninstall", "--remove-data", "--yes")

        assert (endpoint["root"] / "install" / "install.sh").exists()


class TestNamedInstances:
    def test_the_project_follows_the_instance(self, endpoint):
        state = endpoint["root"] / ".env.install-state"
        state.write_text(state.read_text().replace("EP_INSTANCE=ndp", "EP_INSTANCE=glsr"))

        result = _run(endpoint, "status")

        assert "instance: glsr" in result.stdout
        assert "compose project: ndp-ep-glsr" in result.stdout


def test_from_the_web_it_acts_on_the_installed_checkout(endpoint):
    """Piped, it must not fetch or move the checkout: it only looks at it."""
    lone = endpoint["tmp"] / "piped" / "install.sh"
    lone.parent.mkdir()
    shutil.copy(REPO / "install" / "install.sh", lone)

    result = _run(endpoint, "status", script=lone)

    assert result.returncode == 0, result.stdout + result.stderr
    assert "Fetching" not in result.stdout
    assert f"Endpoint at {endpoint['root']}" in result.stdout


def test_from_the_web_without_an_installation_it_says_so(endpoint, tmp_path):
    lone = tmp_path / "piped" / "install.sh"
    lone.parent.mkdir()
    shutil.copy(REPO / "install" / "install.sh", lone)
    shutil.rmtree(endpoint["root"])

    result = _run(endpoint, "stop", script=lone)

    assert result.returncode != 0
    assert "No Endpoint installed" in result.stderr


def test_an_install_records_its_port(tmp_path):
    root = tmp_path / "ep-api"
    shutil.copytree(REPO / "install", root / "install")
    shutil.copy(REPO / "example.env", root / "example.env")
    shutil.copy(REPO / "docker-compose.yml", root / "docker-compose.yml")
    stubs = tmp_path / "bin"
    stubs.mkdir()
    (stubs / "docker").write_text("#!/bin/sh\nexit 0\n")
    (stubs / "docker").chmod(0o755)

    subprocess.run(
        [
            BASH,
            str(root / "install" / "install.sh"),
            "--backend",
            "none",
            "--no-netbird",
            "--ep-api-port",
            "8123",
            "--yes",
            "--no-start",
        ],
        capture_output=True,
        text=True,
        timeout=120,
        env={**os.environ, "PATH": f"{stubs}{os.pathsep}{os.environ['PATH']}"},
        stdin=subprocess.DEVNULL,
    )

    state = (root / ".env.install-state").read_text()
    assert "EP_API_PORT=8123" in state.splitlines()
