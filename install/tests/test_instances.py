"""
Several Endpoints on one host (issue #355).

``docker-compose.yml`` fixed every container name and the host ports of the
bundled services, so a second installation could not start next to the first.
``install.sh --instance <name>`` now runs an Endpoint as its own Compose
project, with its own container names and free host ports. Without
``--instance`` nothing changes: same names, same ports, same ``.env``.
"""

import os
import re
import shutil
import socket
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
BASH = shutil.which("bash")

pytestmark = pytest.mark.skipif(
    BASH is None or os.name == "nt",
    reason="needs bash with /dev/tcp; the stubs are POSIX shell scripts",
)


def _compose():
    return (REPO / "docker-compose.yml").read_text(encoding="utf-8")


def test_every_container_name_follows_the_instance():
    names = re.findall(r"container_name: (\S+)", _compose())

    assert names
    for name in names:
        assert name.startswith("${EP_INSTANCE:-ndp}-"), name


@pytest.mark.parametrize(
    "variable, default, inside",
    [
        ("MONGODB_HOST_PORT", 27018, 27017),
        ("MINIO_HOST_PORT", 9002, 9000),
        ("MINIO_CONSOLE_HOST_PORT", 9003, 9001),
        ("KAFKA_HOST_PORT", 9094, 9092),
        ("KAFKA_INTERNAL_HOST_PORT", 9095, 9093),
        ("KAFKA_UI_HOST_PORT", 8081, 8080),
    ],
)
def test_bundled_service_ports_can_move_and_default_as_before(
    variable, default, inside
):
    assert f'"${{{variable}:-{default}}}:{inside}"' in _compose()


def _installer(tmp_path):
    checkout = tmp_path / "ep-api"
    if not checkout.exists():
        shutil.copytree(REPO / "install", checkout / "install")
        shutil.copy(REPO / "example.env", checkout / "example.env")
        shutil.copy(REPO / "docker-compose.yml", checkout / "docker-compose.yml")
        stubs = tmp_path / "bin"
        stubs.mkdir()
        (stubs / "docker").write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        (stubs / "curl").write_text("#!/bin/sh\nprintf 000\nexit 7\n", encoding="utf-8")
        for stub in stubs.iterdir():
            stub.chmod(0o755)
    return checkout


def _run(tmp_path, *args):
    checkout = _installer(tmp_path)
    return subprocess.run(
        [BASH, str(checkout / "install" / "install.sh"), *args, "--yes", "--no-start"],
        capture_output=True,
        text=True,
        timeout=120,
        env={
            **os.environ,
            "PATH": f"{tmp_path / 'bin'}{os.pathsep}{os.environ['PATH']}",
        },
        stdin=subprocess.DEVNULL,
    )


def _env(tmp_path):
    text = (tmp_path / "ep-api" / ".env").read_text(encoding="utf-8")
    return dict(
        line.split("=", 1) for line in text.splitlines() if re.match(r"^[A-Z_]+=", line)
    )


def _state(tmp_path):
    text = (tmp_path / "ep-api" / ".env.install-state").read_text(encoding="utf-8")
    return dict(line.split("=", 1) for line in text.splitlines() if "=" in line)


@pytest.fixture
def busy_mongodb_port():
    """The default MongoDB host port is taken, as by another Endpoint."""
    with socket.socket() as server:
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            server.bind(("127.0.0.1", 27018))
        except OSError:
            pass  # already taken on this machine, which is just as good
        else:
            server.listen()
        yield


def test_a_single_endpoint_is_unchanged(tmp_path):
    result = _run(tmp_path, "--backend", "mongodb", "--s3")

    assert result.returncode == 0, result.stdout + result.stderr
    env = _env(tmp_path)
    for variable in (
        "EP_INSTANCE",
        "COMPOSE_PROJECT_NAME",
        "MONGODB_HOST_PORT",
        "MINIO_HOST_PORT",
    ):
        assert variable not in env


def test_a_named_instance_gets_its_own_project_and_free_ports(
    tmp_path, busy_mongodb_port
):
    result = _run(
        tmp_path,
        "--instance",
        "glsr",
        "--backend",
        "mongodb",
        "--s3",
        "--ep-api-port",
        "8062",
    )

    assert result.returncode == 0, result.stdout + result.stderr
    env = _env(tmp_path)
    assert env["EP_INSTANCE"] == "glsr"
    assert env["COMPOSE_PROJECT_NAME"] == "ndp-ep-glsr"
    assert env["MONGODB_HOST_PORT"] != "27018"
    assert len({env["MINIO_HOST_PORT"], env["MINIO_CONSOLE_HOST_PORT"]}) == 2


def test_a_re_run_keeps_the_instance_and_its_ports(tmp_path, busy_mongodb_port):
    _run(
        tmp_path, "--instance", "glsr", "--backend", "mongodb", "--ep-api-port", "8062"
    )
    first = _env(tmp_path)

    # The upgrade: same checkout, no --instance, its own ports now in use.
    with socket.socket() as own:
        own.bind(("127.0.0.1", int(first["MONGODB_HOST_PORT"])))
        own.listen()
        result = _run(tmp_path, "--backend", "mongodb", "--ep-api-port", "8062")

    assert result.returncode == 0, result.stdout + result.stderr
    again = _env(tmp_path)
    assert again["EP_INSTANCE"] == "glsr"
    assert again["MONGODB_HOST_PORT"] == first["MONGODB_HOST_PORT"]
    assert _state(tmp_path)["EP_INSTANCE"] == "glsr"


def test_an_installed_endpoint_cannot_be_renamed(tmp_path):
    assert _run(tmp_path, "--backend", "none").returncode == 0

    result = _run(tmp_path, "--instance", "glsr", "--backend", "none")

    assert result.returncode == 1
    assert "already runs the Endpoint 'ndp'" in result.stderr


@pytest.mark.parametrize("name", ["GLSR", "1abc", "a b", "ndp_2"])
def test_an_instance_name_is_checked(tmp_path, name):
    result = _run(tmp_path, "--instance", name, "--backend", "none")

    assert result.returncode == 1
    assert "--instance must start with a letter" in result.stderr


@pytest.fixture
def busy_ckan_port():
    """CKAN's default https port is taken, as by the first Endpoint's CKAN."""
    with socket.socket() as server:
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            server.bind(("127.0.0.1", 8443))
        except OSError:
            pass
        else:
            server.listen()
        yield


def _ckan_plan(tmp_path, *args):
    """What a dry run says about the CKAN it would install (issue #357)."""
    result = _run(tmp_path, "--backend", "ckan", "--dry-run", *args)
    assert result.returncode == 0, result.stdout + result.stderr
    where = re.search(
        r"CKAN would be installed at (\S+)", result.stderr + result.stdout
    )
    url = re.search(r"^CKAN_URL=(\S+)", result.stdout, re.M)
    return where.group(1), url.group(1) if url else ""


def test_a_named_instance_installs_its_own_ckan(tmp_path, busy_ckan_port):
    where, url = _ckan_plan(tmp_path, "--instance", "glsr", "--ep-api-port", "8062")

    assert where == str(tmp_path / "ndp-ckan-glsr")
    assert not url.endswith(":8443"), url


def test_a_single_endpoint_still_installs_ckan_where_it_did(tmp_path):
    where, url = _ckan_plan(tmp_path)

    assert where == str(tmp_path / "ndp-ckan")
    assert url.endswith(":8443"), url


def test_ckan_ports_given_by_the_operator_are_kept(tmp_path, busy_ckan_port):
    _, url = _ckan_plan(
        tmp_path,
        "--instance",
        "glsr",
        "--ckan-ssl-port",
        "9443",
        "--ep-api-port",
        "8062",
    )

    assert url.endswith(":9443"), url
