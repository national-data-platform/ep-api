"""
Re-running the installer does what the command line says (issues #415, #416).

#415:

1. Remembered settings replaced options given on the command line, so with a
   remembered ``backend=none``, ``--backend ckan`` installed no catalog.
2. The port question re-negotiated ``--ep-api-port``, and on a re-run it
   offered the next port because the Endpoint's own container held it.
3. ``--dry-run`` wrote the answers to the Federation.

#416: on a re-run, ``.env already exists. Overwrite? [y/N]`` came after all
the work (building CKAN, joining NetBird) and Enter meant No, so the run
ended having changed nothing.

The prompts only appear on a terminal, so the installer runs under a
pseudo-terminal against a stand-in Federation on localhost.
"""

import json
import os
import pty
import select
import shutil
import socket
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

CONFIG_ID = "cfg415"
REGISTRATION = {"organization": "ORG-415", "ep_name": "EP-415"}


def _federation(remembered):
    state = {"puts": []}

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802
            if self.path == f"/ep/{CONFIG_ID}/settings":
                body = {"settings": remembered}
            elif self.path == f"/ep/{CONFIG_ID}":
                body = REGISTRATION
            else:
                self.send_response(404)
                self.end_headers()
                return
            data = json.dumps(body).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_PUT(self):  # noqa: N802
            length = int(self.headers.get("Content-Length", 0))
            state["puts"].append(self.rfile.read(length))
            self.send_response(200)
            self.end_headers()

        def log_message(self, *args):
            pass

    server = HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    state["url"] = f"http://127.0.0.1:{server.server_address[1]}"
    state["server"] = server
    return state


@pytest.fixture
def federation():
    started = []

    def start(remembered):
        state = _federation(remembered)
        started.append(state)
        return state

    yield start
    for state in started:
        state["server"].shutdown()


@pytest.fixture
def checkout(tmp_path):
    root = tmp_path / "ep-api"
    shutil.copytree(REPO / "install", root / "install")
    shutil.copy(REPO / "example.env", root / "example.env")
    return root


def _stubs(tmp_path, docker_script="#!/bin/sh\nexit 0\n"):
    stubs = tmp_path / "bin"
    stubs.mkdir(exist_ok=True)
    (stubs / "docker").write_text(docker_script, encoding="utf-8")
    (stubs / "docker").chmod(0o755)
    # Only the stand-in Federation is reachable.
    (stubs / "curl").write_text(
        "#!/bin/sh\n"
        'case "$*" in\n'
        f'  *127.0.0.1*) exec "{REAL_CURL}" "$@" ;;\n'
        "esac\n"
        "printf 000\n"
        "exit 7\n",
        encoding="utf-8",
    )
    (stubs / "curl").chmod(0o755)
    return stubs


def _run(checkout, stubs, args, answer=lambda line: ""):
    """Run the installer on a terminal, answering each prompt with answer()."""
    env = {
        **os.environ,
        "PATH": f"{stubs}{os.pathsep}{os.environ['PATH']}",
        "TERM": "dumb",
    }
    main, child = pty.openpty()
    process = subprocess.Popen(
        [BASH, str(checkout / "install" / "install.sh"), *args],
        stdin=child,
        stdout=child,
        stderr=child,
        env=env,
        cwd=checkout,
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
        pytest.fail(
            "install.sh did not finish; it was waiting after:\n" + output[-2000:]
        )
    os.close(main)
    return process.returncode, output, prompts


def _remember(line):
    if "Federation configuration to remember" in line:
        return "y"
    if "NDP access token" in line:
        return "token-415"
    return ""


def _rendered(output):
    return dict(
        line.strip().split("=", 1)
        for line in output.splitlines()
        if "=" in line and line.strip().split("=", 1)[0].isupper()
    )


def _free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


# ---------------------------------------------------------------- #415 (1)


def test_backend_on_the_command_line_beats_the_remembered_one(
    federation, checkout, tmp_path
):
    fed = federation({"backend": "none"})
    code, output, prompts = _run(
        checkout,
        _stubs(tmp_path),
        [
            "--config-id",
            CONFIG_ID,
            "--federation-url",
            fed["url"],
            "--backend",
            "ckan",
            "--dry-run",
        ],
        _remember,
    )

    assert code == 0, output
    assert "Loaded the settings remembered" in output, output
    assert any("Choice [4]" in p for p in prompts), prompts
    assert _rendered(output)["LOCAL_CATALOG_BACKEND"] == "ckan"


def test_a_remembered_catalog_url_does_not_follow_a_different_backend(
    federation, checkout, tmp_path
):
    """A remembered existing MongoDB does not turn --backend ckan into 'existing CKAN'."""
    fed = federation({"backend": "mongodb", "mongodb_url": "mongodb://m:27017"})
    code, output, prompts = _run(
        checkout,
        _stubs(tmp_path),
        [
            "--config-id",
            CONFIG_ID,
            "--federation-url",
            fed["url"],
            "--backend",
            "ckan",
            "--dry-run",
        ],
        _remember,
    )

    assert code == 0, output
    assert any("Choice [4]" in p for p in prompts), prompts


def test_the_port_on_the_command_line_beats_the_remembered_one(
    federation, checkout, tmp_path
):
    port = _free_port()
    fed = federation({"ep_api_port": "9999"})
    code, output, prompts = _run(
        checkout,
        _stubs(tmp_path),
        [
            "--config-id",
            CONFIG_ID,
            "--federation-url",
            fed["url"],
            "--ep-api-port",
            str(port),
            "--dry-run",
        ],
        _remember,
    )

    assert code == 0, output
    assert any(f"[{port}]" in p for p in prompts if "Port to publish" in p), prompts
    assert _rendered(output)["EP_API_PORT"] == str(port)


def test_what_the_command_line_does_not_say_is_still_remembered(
    federation, checkout, tmp_path
):
    fed = federation({"backend": "mongodb"})
    code, output, prompts = _run(
        checkout,
        _stubs(tmp_path),
        ["--config-id", CONFIG_ID, "--federation-url", fed["url"], "--dry-run"],
        _remember,
    )

    assert code == 0, output
    assert any("Choice [2]" in p for p in prompts), prompts


# ---------------------------------------------------------------- #415 (2)


def test_a_busy_port_given_on_the_command_line_is_not_moved(
    federation, checkout, tmp_path
):
    """The port the operator chose is offered as it is, even when in use."""
    fed = federation({})
    with socket.socket() as busy:
        busy.bind(("127.0.0.1", 0))
        busy.listen()
        port = busy.getsockname()[1]
        code, output, prompts = _run(
            checkout,
            _stubs(tmp_path),
            [
                "--config-id",
                CONFIG_ID,
                "--federation-url",
                fed["url"],
                "--ep-api-port",
                str(port),
                "--dry-run",
            ],
        )

    assert code == 0, output
    assert any(f"[{port}]" in p for p in prompts if "Port to publish" in p), prompts


def test_a_port_held_by_this_endpoint_is_offered_again(federation, checkout, tmp_path):
    """On a re-run the Endpoint's own container holds its port (as in #332)."""
    fed = federation({"ep_api_port": "0"})
    docker = (
        "#!/bin/sh\n"
        'case "$1" in\n'
        '  ps) printf "ndp-ep-api\\t0.0.0.0:%s->8000/tcp\\n" "$HELD_PORT" ;;\n'
        f'  inspect) echo "{checkout}" ;;\n'
        "esac\n"
        "exit 0\n"
    )
    with socket.socket() as busy:
        busy.bind(("127.0.0.1", 0))
        busy.listen()
        port = busy.getsockname()[1]
        os.environ["HELD_PORT"] = str(port)
        try:
            (checkout / ".env.install-state").write_text(
                f"EP_INSTANCE=ndp\nEP_API_PORT={port}\n", encoding="utf-8"
            )
            fed_state = federation({"ep_api_port": str(port)})
            code, output, prompts = _run(
                checkout,
                _stubs(tmp_path, docker),
                [
                    "--config-id",
                    CONFIG_ID,
                    "--federation-url",
                    fed_state["url"],
                    "--dry-run",
                ],
                _remember,
            )
        finally:
            del os.environ["HELD_PORT"]

    assert code == 0, output
    port_prompts = [p for p in prompts if "Port to publish" in p]
    assert any(f"[{port}]" in p for p in port_prompts), port_prompts


# ---------------------------------------------------------------- #415 (3)


def test_a_dry_run_does_not_write_to_the_federation(federation, checkout, tmp_path):
    fed = federation({"backend": "none"})
    code, output, _ = _run(
        checkout,
        _stubs(tmp_path),
        ["--config-id", CONFIG_ID, "--federation-url", fed["url"], "--dry-run"],
        _remember,
    )

    assert code == 0, output
    assert fed["puts"] == []
    assert "Saved these answers" not in output
    assert "would save" in output.lower(), output


# ---------------------------------------------------------------- #416


def _rerun(checkout, tmp_path, fed, extra=(), answer=lambda line: ""):
    (checkout / ".env").write_text("EP_NAME=old\n", encoding="utf-8")
    return _run(
        checkout,
        _stubs(tmp_path),
        [
            "--config-id",
            CONFIG_ID,
            "--federation-url",
            fed["url"],
            "--no-start",
            *extra,
        ],
        answer,
    )


def test_the_overwrite_question_comes_before_any_work(federation, checkout, tmp_path):
    fed = federation({})
    code, output, prompts = _rerun(checkout, tmp_path, fed)

    asked = output.find("already exists. Overwrite")
    assert asked != -1, output
    assert asked < output.find("Fetching the Federation registration"), output
    assert asked < output.find("Selecting the local catalog backend"), output


def test_enter_on_a_rerun_updates_the_endpoint(federation, checkout, tmp_path):
    fed = federation({})
    code, output, prompts = _rerun(checkout, tmp_path, fed)

    assert any("Overwrite" in p and "[Y/n]" in p for p in prompts), prompts
    assert code == 0, output
    assert "EP-415" in (checkout / ".env").read_text(encoding="utf-8")
    assert list(checkout.glob(".env.backup.*")), "the previous .env is kept"


def test_no_stops_before_doing_anything(federation, checkout, tmp_path):
    fed = federation({})
    code, output, _ = _rerun(
        checkout,
        tmp_path,
        fed,
        answer=lambda line: "n" if "Overwrite" in line else "",
    )

    assert code != 0
    assert "Selecting the local catalog backend" not in output, output
    assert (checkout / ".env").read_text(encoding="utf-8") == "EP_NAME=old\n"


def test_overwrite_env_skips_only_that_question(federation, checkout, tmp_path):
    fed = federation({})
    code, output, prompts = _rerun(checkout, tmp_path, fed, extra=["--overwrite-env"])

    assert code == 0, output
    assert not any("Overwrite" in p for p in prompts), prompts
    assert any(
        "Port to publish" in p for p in prompts
    ), "other questions are still asked"
    assert list(checkout.glob(".env.backup.*"))
