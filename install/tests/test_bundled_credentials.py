"""
The MongoDB and MinIO the installer starts get credentials of their own
(issue #375).

They were created with the same demo pairs on every Endpoint
(``admin``/``admin123``, ``minioadmin``/``minioadmin123``), and a named
instance publishes both on host ports, so the database and the object store
were reachable on the LAN behind passwords anyone can look up. A new
installation now generates them, keeps them in the install state and reuses
them on re-runs. An installation whose MongoDB or MinIO already holds data
keeps the credentials it was created with: changing them would lock the
Endpoint out of its own data.

It also says when it turns CKAN certificate checks off (``CKAN_VERIFY_SSL``),
which it did silently.

``docker`` is a stub: nothing is started.
"""

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

BUNDLED = re.compile(r"^mongodb://admin:(?P<password>[^@]+)@mongodb:27017$")


def _checkout(tmp_path, name="ep-api"):
    root = tmp_path / name
    shutil.copytree(REPO / "install", root / "install")
    shutil.copy(REPO / "example.env", root / "example.env")
    shutil.copy(REPO / "docker-compose.yml", root / "docker-compose.yml")
    return root


@pytest.fixture
def stubs(tmp_path):
    """A docker that answers, and knows the volumes listed in volumes.txt."""
    directory = tmp_path / "bin"
    directory.mkdir()
    volumes = tmp_path / "volumes.txt"
    volumes.write_text("", encoding="utf-8")
    (directory / "docker").write_text(
        "#!/bin/sh\n"
        'if [ "$1" = volume ] && [ "$2" = inspect ]; then\n'
        f'  grep -qx "$3" "{volumes}"\n'
        "  exit $?\n"
        "fi\n"
        "exit 0\n",
        encoding="utf-8",
    )
    (directory / "docker").chmod(0o755)
    return {"bin": directory, "volumes": volumes}


def _install(root, stubs, *args):
    return subprocess.run(
        [
            BASH,
            str(root / "install" / "install.sh"),
            "--no-netbird",
            *args,
            "--yes",
            "--no-start",
        ],
        capture_output=True,
        text=True,
        timeout=120,
        env={**os.environ, "PATH": f"{stubs['bin']}{os.pathsep}{os.environ['PATH']}"},
        stdin=subprocess.DEVNULL,
    )


def _env(root):
    text = (root / ".env").read_text(encoding="utf-8")
    return dict(
        (key, value.strip('"'))
        for key, value in (
            line.split("=", 1)
            for line in text.splitlines()
            if re.match(r"^[A-Z0-9_]+=", line)
        )
    )


def _state(root):
    path = root / ".env.install-state"
    if not path.exists():
        return {}
    return dict(
        line.split("=", 1) for line in path.read_text().splitlines() if "=" in line
    )


def _mongo_password(root):
    match = BUNDLED.match(_env(root)["MONGODB_CONNECTION_STRING"])
    assert match, _env(root)["MONGODB_CONNECTION_STRING"]
    return match["password"]


class TestMongoDB:
    def test_a_new_installation_gets_its_own_password(self, tmp_path, stubs):
        root = _checkout(tmp_path)

        result = _install(root, stubs, "--backend", "mongodb")

        assert result.returncode == 0, result.stdout + result.stderr
        password = _mongo_password(root)
        assert password != "admin123"
        assert len(password) >= 20
        assert _env(root)["MONGODB_ROOT_PASSWORD"] == password

    def test_it_is_kept_in_the_install_state_and_reused(self, tmp_path, stubs):
        root = _checkout(tmp_path)
        _install(root, stubs, "--backend", "mongodb")
        first = _mongo_password(root)

        _install(root, stubs, "--backend", "mongodb")

        assert _mongo_password(root) == first
        assert _state(root)["MONGODB_ROOT_PASSWORD"] == first

    def test_two_endpoints_do_not_share_it(self, tmp_path, stubs):
        one = _checkout(tmp_path, "one")
        two = _checkout(tmp_path, "two")

        _install(one, stubs, "--backend", "mongodb")
        _install(two, stubs, "--backend", "mongodb")

        assert _mongo_password(one) != _mongo_password(two)

    def test_access_requests_get_one_too(self, tmp_path, stubs):
        root = _checkout(tmp_path)

        _install(root, stubs, "--backend", "none", "--access-requests")

        assert _mongo_password(root) != "admin123"

    def test_an_endpoint_installed_before_keeps_its_password(self, tmp_path, stubs):
        """Its MongoDB was created with admin123 and only accepts that."""
        root = _checkout(tmp_path)
        (root / ".env").write_text(
            "MONGODB_CONNECTION_STRING=mongodb://admin:admin123@mongodb:27017\n",
            encoding="utf-8",
        )
        (root / ".env.install-state").write_text("EP_INSTANCE=ndp\n")

        result = _install(root, stubs, "--backend", "mongodb")

        assert result.returncode == 0, result.stdout + result.stderr
        assert _mongo_password(root) == "admin123"
        assert _env(root)["MONGODB_ROOT_PASSWORD"] == "admin123"
        assert "demo password" in result.stderr

    def test_a_mongodb_volume_left_behind_keeps_the_demo_password(
        self, tmp_path, stubs
    ):
        """No .env, but the data is there, created with the old password."""
        root = _checkout(tmp_path)
        stubs["volumes"].write_text("ep-api_mongodb_data\n", encoding="utf-8")

        _install(root, stubs, "--backend", "mongodb")

        assert _mongo_password(root) == "admin123"

    def test_an_external_mongodb_is_left_alone(self, tmp_path, stubs):
        root = _checkout(tmp_path)

        _install(
            root, stubs, "--backend", "mongodb", "--mongodb-url", "mongodb://db:27017"
        )

        assert _env(root)["MONGODB_CONNECTION_STRING"] == "mongodb://db:27017"


class TestMinIO:
    def test_a_new_installation_gets_its_own_keys(self, tmp_path, stubs):
        root = _checkout(tmp_path)

        result = _install(root, stubs, "--backend", "none", "--s3")

        assert result.returncode == 0, result.stdout + result.stderr
        env = _env(root)
        assert env["S3_ACCESS_KEY"] != "minioadmin"
        assert env["S3_SECRET_KEY"] != "minioadmin123"
        assert len(env["S3_SECRET_KEY"]) >= 20

    def test_they_are_reused_on_a_rerun(self, tmp_path, stubs):
        root = _checkout(tmp_path)
        _install(root, stubs, "--backend", "none", "--s3")
        first = _env(root)

        _install(root, stubs, "--backend", "none", "--s3")

        assert _env(root)["S3_ACCESS_KEY"] == first["S3_ACCESS_KEY"]
        assert _env(root)["S3_SECRET_KEY"] == first["S3_SECRET_KEY"]

    def test_an_endpoint_installed_before_keeps_its_keys(self, tmp_path, stubs):
        root = _checkout(tmp_path)
        (root / ".env").write_text(
            "S3_ENDPOINT=minio:9000\n"
            "S3_ACCESS_KEY=minioadmin\n"
            "S3_SECRET_KEY=minioadmin123\n",
            encoding="utf-8",
        )
        (root / ".env.install-state").write_text("EP_INSTANCE=ndp\n")

        _install(root, stubs, "--backend", "none", "--s3")

        assert _env(root)["S3_ACCESS_KEY"] == "minioadmin"
        assert _env(root)["S3_SECRET_KEY"] == "minioadmin123"

    def test_an_external_s3_is_left_alone(self, tmp_path, stubs):
        root = _checkout(tmp_path)

        _install(
            root,
            stubs,
            "--backend",
            "none",
            "--s3-endpoint",
            "s3.example.invalid",
            "--s3-access-key",
            "AK",
            "--s3-secret-key",
            "SK",
        )

        assert _env(root)["S3_ACCESS_KEY"] == "AK"
        assert _env(root)["S3_SECRET_KEY"] == "SK"


class TestComposeReadsThem:
    """The containers must start with what the Endpoint connects with."""

    def test_mongodb_takes_its_password_from_the_environment(self):
        text = (REPO / "docker-compose.yml").read_text(encoding="utf-8")

        assert "MONGO_INITDB_ROOT_PASSWORD: ${MONGODB_ROOT_PASSWORD:-admin123}" in text

    def test_minio_takes_its_keys_from_the_environment(self):
        text = (REPO / "docker-compose.yml").read_text(encoding="utf-8")

        assert "MINIO_ROOT_USER: ${S3_ACCESS_KEY:-minioadmin}" in text
        assert "MINIO_ROOT_PASSWORD: ${S3_SECRET_KEY:-minioadmin123}" in text

    def test_no_fixed_password_is_left_outside_a_default(self):
        text = (REPO / "docker-compose.yml").read_text(encoding="utf-8")
        code = "\n".join(
            line for line in text.splitlines() if not line.lstrip().startswith("#")
        )

        for literal in ("admin123", "minioadmin"):
            for match in re.finditer(literal, code):
                line = code[: match.start()].rsplit("\n", 1)[-1]
                assert ":-" in line, f"fixed {literal}: {line}"


@pytest.fixture
def ckan():
    """A reachable CKAN, so the installer reuses the one it installed before."""

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.end_headers()

        def log_message(self, *args):
            pass

    server = HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()


def test_turning_ckan_certificate_checks_off_is_said(tmp_path, stubs, ckan):
    root = _checkout(tmp_path)
    (root / ".env.install-state").write_text(
        f"CKAN_API_KEY=key\nCKAN_URL={ckan}\nCKAN_SYSADMIN=ckan_admin\n"
    )

    result = _install(root, stubs, "--backend", "ckan")

    assert result.returncode == 0, result.stdout + result.stderr
    assert _env(root)["CKAN_VERIFY_SSL"] == "False"
    assert "CKAN_VERIFY_SSL=False" in result.stderr
    assert "self-signed" in result.stderr
