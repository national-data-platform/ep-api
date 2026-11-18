"""
Which authentication service (AAI) an installed Endpoint uses (issue #365).

``--env test`` pointed the installer at the test Federation, but
``AUTH_API_URL`` stayed on the production identity provider, so an Endpoint
installed for the test platform refused every token from it. Nor could a
remembered AAI URL, or one named by the Federation, take its place: the prompt
always offered production, and unattended runs had no way to set it at all.

``KEYCLOAK_URL`` (the identity provider's host; ``AUTH_API_URL`` before
#389) now comes from, first to last:

1. ``--auth-api-url``;
2. the remembered settings, or what was typed at the prompt;
3. the ``auth_api_url`` the Federation returns with the configuration
   (sci-ndp/ndp-federation#134);
4. the test identity provider with ``--env test`` (or the test Federation's
   URL), production otherwise.

Unattended runs use ``--yes --no-start`` against a stand-in Federation; the
prompt is checked under a pseudo-terminal with ``--dry-run``.
"""

import json
import os
import pty
import re
import select
import shutil
import subprocess
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
BASH = shutil.which("bash")
REAL_CURL = shutil.which("curl")

pytestmark = pytest.mark.skipif(
    BASH is None or os.name == "nt" or REAL_CURL is None,
    reason="needs bash, curl and a pseudo-terminal",
)

CONFIG_ID = "cfg365"
OWNER_TOKEN = "owner-token-365"
PROD = "https://idp.nationaldataplatform.org"
TEST = "https://idp-test.nationaldataplatform.org"
# What the Federation, older remembered settings and older scripts name: the
# AAI's /information URL. Only the host is written.
FEDERATION_AAI = "https://aai.selfhosted.example/temp/information"
REMEMBERED_AAI = "https://aai.remembered.example/temp/information"
GIVEN_AAI = "https://aai.given.example/temp/information"


def host_of(url):
    return "/".join(url.split("/")[:3])


@pytest.fixture
def federation():
    served = {
        "config": {
            "_id": CONFIG_ID,
            "organization": "ORG-365",
            "ep_name": "EP-365",
        },
        "settings": {},
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
                self._send({"settings": served["settings"]})
            else:
                self._send({"detail": "not found"}, 404)

        def do_PUT(self):  # noqa: N802
            self.rfile.read(int(self.headers.get("Content-Length", 0)))
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
        '[ "$1 $2" = "volume inspect" ] && exit 1\n'
        "exit 0\n",
        encoding="utf-8",
    )
    # Only the stand-in Federation is reachable: the AAI URLs are never
    # contacted for real.
    (stubs / "curl").write_text(
        "#!/bin/sh\n"
        'case "$*" in\n'
        f'  *127.0.0.1*) exec "{REAL_CURL}" "$@" ;;\n'
        "esac\n"
        "printf 000\n"
        "exit 7\n",
        encoding="utf-8",
    )
    for stub in stubs.iterdir():
        stub.chmod(0o755)
    token = tmp_path / "token"
    token.write_text(OWNER_TOKEN, encoding="utf-8")
    return {"checkout": checkout, "stubs": stubs, "token": token}


def _environment(host):
    return {
        **os.environ,
        "PATH": f"{host['stubs']}{os.pathsep}{os.environ['PATH']}",
        "TERM": "dumb",
    }


def _install(host, federation, *args):
    result = subprocess.run(
        [
            BASH,
            str(host["checkout"] / "install" / "install.sh"),
            "--config-id",
            CONFIG_ID,
            "--federation-url",
            federation["url"],
            "--no-netbird",
            "--no-affinities",
            *args,
            "--yes",
            "--no-start",
        ],
        capture_output=True,
        text=True,
        timeout=120,
        env=_environment(host),
        stdin=subprocess.DEVNULL,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return result


def _auth_api_url(host):
    text = (host["checkout"] / ".env").read_text(encoding="utf-8")
    found = re.findall(r"^KEYCLOAK_URL=(.*)$", text, re.MULTILINE)
    assert len(found) == 1, found
    return found[0]


# ------------------------------------------------------------ unattended


def test_without_anything_said_it_is_production(host, federation):
    _install(host, federation)

    assert _auth_api_url(host) == PROD


def test_env_test_uses_the_test_identity_provider(host, federation):
    # What the test platform's create-endpoint page sends: --env test, and
    # here --federation-url as well, which --env does not overrule.
    _install(host, federation, "--env", "test")

    assert _auth_api_url(host) == TEST


def test_env_prod_keeps_production(host, federation):
    _install(host, federation, "--env", "prod")

    assert _auth_api_url(host) == PROD


def test_the_federations_aai_is_used(host, federation):
    federation["config"]["auth_api_url"] = FEDERATION_AAI

    _install(host, federation, "--env", "test")

    assert _auth_api_url(host) == host_of(FEDERATION_AAI)


def test_auth_api_url_option_wins(host, federation):
    federation["config"]["auth_api_url"] = FEDERATION_AAI

    _install(host, federation, "--env", "test", "--auth-api-url", GIVEN_AAI)

    assert _auth_api_url(host) == host_of(GIVEN_AAI)


def test_a_remembered_aai_wins_over_the_federations(host, federation):
    federation["config"]["auth_api_url"] = FEDERATION_AAI
    federation["settings"] = {"auth_api_url": REMEMBERED_AAI}

    _install(host, federation, "--ndp-token-file", str(host["token"]))

    assert _auth_api_url(host) == host_of(REMEMBERED_AAI)


def test_the_option_wins_over_a_remembered_aai(host, federation):
    federation["settings"] = {"auth_api_url": REMEMBERED_AAI}

    _install(
        host,
        federation,
        "--ndp-token-file",
        str(host["token"]),
        "--auth-api-url",
        GIVEN_AAI,
    )

    assert _auth_api_url(host) == host_of(GIVEN_AAI)


def test_the_option_is_documented():
    help_text = subprocess.run(
        [BASH, str(REPO / "install" / "install.sh"), "--help"],
        capture_output=True,
        text=True,
        timeout=30,
    ).stdout

    assert "--auth-api-url" in help_text


# ------------------------------------------------------------ on a terminal


def _run_on_a_terminal(host, args, answer):
    """Run the installer on a pseudo-terminal, answering each prompt."""
    main, child = pty.openpty()
    process = subprocess.Popen(
        [BASH, str(host["checkout"] / "install" / "install.sh"), *args],
        stdin=child,
        stdout=child,
        stderr=child,
        env=_environment(host),
        cwd=host["checkout"],
        close_fds=True,
    )
    os.close(child)
    output, pending, prompts = "", "", []
    deadline = time.time() + 150
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
            if last.endswith(":") or last.endswith("]:"):
                prompts.append(last)
                os.write(main, (answer(last) + "\n").encode())
                pending = ""
        elif process.poll() is not None:
            break
    try:
        process.wait(timeout=30)
    except subprocess.TimeoutExpired:
        process.kill()
        os.close(main)
        pytest.fail("install.sh did not finish:\n" + output[-2000:])
    os.close(main)
    assert process.returncode == 0, output
    rendered = re.findall(r"^\s*KEYCLOAK_URL=(\S*)", output, re.MULTILINE)
    return rendered, prompts


def _remember(line):
    if "Federation configuration to remember" in line:
        return "y"
    if "NDP access token" in line:
        return OWNER_TOKEN
    return ""


def _aai_prompt(prompts):
    found = [p for p in prompts if "Identity provider URL" in p]
    assert len(found) == 1, prompts
    return found[0]


def _terminal_args(federation, *extra):
    return [
        "--config-id",
        CONFIG_ID,
        "--federation-url",
        federation["url"],
        "--no-netbird",
        "--no-affinities",
        *extra,
        "--dry-run",
    ]


def test_the_prompt_offers_the_test_aai_with_env_test(host, federation):
    rendered, prompts = _run_on_a_terminal(
        host, _terminal_args(federation, "--env", "test"), lambda line: ""
    )

    assert f"[{TEST}]" in _aai_prompt(prompts)
    assert rendered == [TEST]


def test_the_prompt_offers_the_remembered_aai(host, federation):
    # The case in the issue: "Loaded the settings remembered for this
    # Endpoint", then the prompt offered production anyway, and Enter
    # installed against it.
    federation["settings"] = {"auth_api_url": REMEMBERED_AAI}

    rendered, prompts = _run_on_a_terminal(host, _terminal_args(federation), _remember)

    assert f"[{REMEMBERED_AAI}]" in _aai_prompt(prompts)
    assert rendered == [host_of(REMEMBERED_AAI)]


def test_enter_at_the_prompt_takes_the_federations_aai(host, federation):
    federation["config"]["auth_api_url"] = FEDERATION_AAI

    rendered, prompts = _run_on_a_terminal(
        host, _terminal_args(federation), lambda line: ""
    )

    assert rendered == [host_of(FEDERATION_AAI)]


def test_what_is_typed_at_the_prompt_wins(host, federation):
    federation["config"]["auth_api_url"] = FEDERATION_AAI

    def answer(line):
        return GIVEN_AAI if "Identity provider URL" in line else ""

    rendered, _ = _run_on_a_terminal(host, _terminal_args(federation), answer)

    assert rendered == [host_of(GIVEN_AAI)]
