"""
Installer options for unattended and self-hosted installs (issues #413,
#414, #417, #418, #419).

- #413: ``--ckan-global-url`` sets ``CKAN_GLOBAL_URL``; Endpoints installed for
  another platform searched production's global catalog.
- #414: Affinities is on by default when the configuration holds both the
  Affinities URL and this Endpoint's id; ``--no-affinities`` opts out.
- #417: an unattended run with the owner's token (``--ndp-token-file``)
  loads the remembered settings; only terminals did.
- #418: ``--bind <address>`` publishes every port on that address.
- #419: MongoDB and MinIO credentials are left empty when neither is
  installed, instead of ``example.env``'s published demo values.

Each test runs the real installer (``--yes --no-start``, so ``.env`` is
written and nothing is started) against a stand-in Federation; ``docker``,
``netbird`` and ``sudo`` are stubs.
"""

import json
import os
import re
import shutil
import subprocess
import sys
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

CONFIG_ID = "cfg413"
OWNER_TOKEN = "owner-token-417"
AFFINITIES_URL = "https://affinities.example.org"


@pytest.fixture
def federation():
    served = {
        "config": {
            "_id": CONFIG_ID,
            "organization": "ORG-413",
            "ep_name": "EP-413",
            "group_name": f"ndp_ep/ep-{CONFIG_ID}",
        },
        "settings": {},
        "puts": [],
    }

    class Handler(BaseHTTPRequestHandler):
        def _send(self, body, status=200):
            data = json.dumps(body).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):  # noqa: N802
            if self.path == f"/ep/{CONFIG_ID}":
                self._send(served["config"])
            elif self.path == f"/ep/{CONFIG_ID}/settings":
                if self.headers.get("Authorization") != f"Bearer {OWNER_TOKEN}":
                    self._send({"detail": "no"}, 403)
                else:
                    self._send({"settings": served["settings"]})
            else:
                self._send({"detail": "not found"}, 404)

        def do_PUT(self):  # noqa: N802
            length = int(self.headers.get("Content-Length", 0))
            served["puts"].append(self.rfile.read(length))
            self._send({})

        def log_message(self, *args):
            pass

    server = HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    served["url"] = f"http://127.0.0.1:{server.server_address[1]}"
    yield served
    server.shutdown()


@pytest.fixture
def host(tmp_path):
    checkout = tmp_path / "ep-api"
    shutil.copytree(REPO / "install", checkout / "install")
    shutil.copy(REPO / "example.env", checkout / "example.env")
    shutil.copy(REPO / "docker-compose.yml", checkout / "docker-compose.yml")
    stubs = tmp_path / "bin"
    stubs.mkdir()
    (stubs / "docker").write_text(
        "#!/bin/sh\n"
        '[ "$1 $2 $3" = "compose version --short" ] && { echo 2.40.3; exit 0; }\n'
        "# No data volume is left from an earlier install.\n"
        '[ "$1 $2" = "volume inspect" ] && exit 1\n'
        "exit 0\n",
        encoding="utf-8",
    )
    (stubs / "netbird").write_text(
        '#!/bin/sh\nprintf \'{"management":{"connected":false}}\'\n',
        encoding="utf-8",
    )
    (stubs / "sudo").write_text('#!/bin/sh\n[ "$1" = "-n" ] && shift\nexec "$@"\n')
    for stub in stubs.iterdir():
        stub.chmod(0o755)
    token = tmp_path / "token"
    token.write_text(OWNER_TOKEN, encoding="utf-8")
    return {"checkout": checkout, "stubs": stubs, "token": token}


def _install(host, federation, *args, backend=("--backend", "none")):
    return subprocess.run(
        [
            BASH,
            str(host["checkout"] / "install" / "install.sh"),
            "--config-id",
            CONFIG_ID,
            "--federation-url",
            federation["url"],
            "--no-netbird",
            *backend,
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
        line.split("=", 1)
        for line in text.splitlines()
        if re.match(r"^[A-Z0-9_]+=", line)
    )


def _ok(result):
    assert result.returncode == 0, result.stdout + result.stderr
    return result


# ------------------------------------------------------------------ #413


def test_the_global_catalog_can_be_chosen(host, federation):
    _ok(_install(host, federation, "--ckan-global-url", "https://portal.test/catalog"))

    assert _env(host)["CKAN_GLOBAL_URL"] == "https://portal.test/catalog"


def test_without_it_the_default_global_catalog_is_kept(host, federation):
    _ok(_install(host, federation))

    assert "CKAN_GLOBAL_URL" not in _env(host)


def test_a_rerun_keeps_the_global_catalog(host, federation):
    _ok(_install(host, federation, "--ckan-global-url", "https://portal.test/catalog"))
    _ok(_install(host, federation))

    assert _env(host)["CKAN_GLOBAL_URL"] == "https://portal.test/catalog"


def test_the_global_catalog_is_one_of_the_remembered_answers():
    sys.path.insert(0, str(REPO / "install"))
    try:
        import remembered_settings
    finally:
        sys.path.pop(0)

    assert "ckan_global_url" in remembered_settings.REMEMBERED_KEYS


# ------------------------------------------------------------------ #414


def _with_affinities(federation, uid="aff-uid-414"):
    federation["config"]["affinities_url"] = AFFINITIES_URL
    if uid:
        federation["config"]["affinities_uid"] = uid


def test_affinities_is_on_when_the_configuration_has_its_id(host, federation):
    _with_affinities(federation)

    _ok(_install(host, federation))

    env = _env(host)
    assert env["AFFINITIES_ENABLED"] == "True"
    assert env["AFFINITIES_URL"] == AFFINITIES_URL
    assert env["AFFINITIES_EP_UUID"] == "aff-uid-414"


def test_no_affinities_turns_it_off_and_is_remembered(host, federation):
    _with_affinities(federation)

    _ok(_install(host, federation, "--no-affinities"))
    assert _env(host)["AFFINITIES_ENABLED"] == "False"

    _ok(_install(host, federation))
    assert _env(host)["AFFINITIES_ENABLED"] == "False"


def test_without_an_affinities_id_it_stays_off(host, federation):
    _with_affinities(federation, uid=None)

    _ok(_install(host, federation))

    assert _env(host)["AFFINITIES_ENABLED"] == "False"


# ------------------------------------------------------------------ #417


def test_an_unattended_run_with_the_token_loads_the_remembered_settings(
    host, federation
):
    federation["settings"] = {
        "backend": "mongodb",
        "auth_api_url": "https://idp.test/temp/information",
        "ep_api_port": "8123",
    }

    result = _ok(
        _install(host, federation, "--ndp-token-file", str(host["token"]), backend=())
    )

    assert "Loaded the settings remembered" in result.stdout
    env = _env(host)
    assert env["LOCAL_CATALOG_BACKEND"] == "mongodb"
    # A remembered auth_api_url becomes KEYCLOAK_URL, keeping only its host.
    assert env["KEYCLOAK_URL"] == "https://idp.test"
    assert env["EP_API_PORT"] == "8123"
    assert federation["puts"] == [], "an unattended run only reads them"


def test_options_still_win_over_them_unattended(host, federation):
    federation["settings"] = {"backend": "mongodb", "ep_api_port": "8123"}

    _ok(
        _install(
            host,
            federation,
            "--ndp-token-file",
            str(host["token"]),
            "--ep-api-port",
            "8124",
        )
    )

    env = _env(host)
    assert env["LOCAL_CATALOG_BACKEND"] == "none"
    assert env["EP_API_PORT"] == "8124"


def test_no_remembered_settings_opts_out(host, federation):
    federation["settings"] = {"backend": "mongodb"}

    result = _ok(
        _install(
            host,
            federation,
            "--ndp-token-file",
            str(host["token"]),
            "--no-remembered-settings",
            backend=(),
        )
    )

    assert "Loaded the settings remembered" not in result.stdout
    assert _env(host)["LOCAL_CATALOG_BACKEND"] == "none"


def test_without_a_token_nothing_is_loaded_and_nothing_fails(host, federation):
    federation["settings"] = {"backend": "mongodb"}

    _ok(_install(host, federation, backend=()))

    assert _env(host)["LOCAL_CATALOG_BACKEND"] == "none"


# ------------------------------------------------------------------ #418


def _override(host):
    path = host["checkout"] / "docker-compose.override.yml"
    return path.read_text(encoding="utf-8") if path.exists() else None


def test_bind_publishes_every_port_on_that_address(host, federation):
    _ok(_install(host, federation, "--bind", "127.0.0.1"))

    override = _override(host)
    assert override is not None
    assert '"127.0.0.1:${EP_API_PORT:-8002}:80"' in override
    assert '"127.0.0.1:${MONGODB_HOST_PORT:-27018}:27017"' in override
    assert '"127.0.0.1:${MINIO_HOST_PORT:-9002}:9000"' in override
    published = re.findall(r'^\s+- "([^"]+)"', override, re.M)
    assert published and all(p.startswith("127.0.0.1:") for p in published)


def test_bind_is_kept_on_a_rerun_and_all_undoes_it(host, federation):
    _ok(_install(host, federation, "--bind", "127.0.0.1"))
    _ok(_install(host, federation))
    assert _override(host) is not None

    _ok(_install(host, federation, "--bind", "all"))
    assert _override(host) is None


def test_without_bind_nothing_changes(host, federation):
    _ok(_install(host, federation))

    assert _override(host) is None


def test_an_override_the_installer_did_not_write_is_left_alone(host, federation):
    mine = host["checkout"] / "docker-compose.override.yml"
    mine.write_text("services: {}\n", encoding="utf-8")

    result = _install(host, federation, "--bind", "127.0.0.1")

    assert result.returncode != 0
    assert "docker-compose.override.yml" in result.stderr
    assert mine.read_text(encoding="utf-8") == "services: {}\n"


def test_a_bind_address_must_be_an_address(host, federation):
    result = _install(host, federation, "--bind", "localhost; rm -rf /")

    assert result.returncode != 0
    assert "--bind" in result.stderr


def test_the_bundled_ckan_is_bound_too(tmp_path):
    """The CKAN project publishes 0.0.0.0:<port> itself; that address is replaced."""
    sys.path.insert(0, str(REPO / "install"))
    try:
        import bind_ports
    finally:
        sys.path.pop(0)
    compose = tmp_path / "docker-compose.yml"
    compose.write_text(
        "services:\n"
        "  nginx:\n"
        "    ports:\n"
        '      - "0.0.0.0:${NGINX_SSLPORT_HOST}:${NGINX_SSLPORT}"\n'
        "  ckan:\n"
        "    image: ckan\n",
        encoding="utf-8",
    )

    text = bind_ports.override(compose.read_text(encoding="utf-8"), "127.0.0.1")

    assert '"127.0.0.1:${NGINX_SSLPORT_HOST}:${NGINX_SSLPORT}"' in text
    assert "0.0.0.0" not in text
    assert "ckan:" not in text


# ------------------------------------------------------------------ #419


def test_unused_mongodb_and_minio_credentials_are_left_empty(host, federation):
    _ok(_install(host, federation))

    env = _env(host)
    for key in (
        "MONGODB_CONNECTION_STRING",
        "MONGODB_ROOT_PASSWORD",
        "S3_ACCESS_KEY",
        "S3_SECRET_KEY",
    ):
        assert env[key] == "", key


def test_installed_services_still_get_generated_credentials(host, federation):
    _ok(_install(host, federation, "--s3", backend=("--backend", "mongodb")))

    env = _env(host)
    assert env["MONGODB_ROOT_PASSWORD"] not in ("", "admin123")
    assert env["MONGODB_CONNECTION_STRING"].startswith("mongodb://admin:")
    assert env["S3_ACCESS_KEY"] not in ("", "minioadmin")
    assert env["S3_SECRET_KEY"] not in ("", "minioadmin123")


def test_an_external_mongodb_is_kept(host, federation):
    _ok(
        _install(
            host,
            federation,
            backend=("--backend", "mongodb", "--mongodb-url", "mongodb://db:27017"),
        )
    )

    env = _env(host)
    assert env["MONGODB_CONNECTION_STRING"] == "mongodb://db:27017"
    assert env["MONGODB_ROOT_PASSWORD"] == ""
