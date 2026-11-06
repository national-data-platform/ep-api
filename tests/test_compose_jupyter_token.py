"""
The bundled JupyterLab has no fixed token (issue #388).

`docker-compose.yml` started JupyterLab with `JUPYTER_TOKEN: testing_token`
and `--NotebookApp.token='testing_token'`, a value published in this
repository, so anyone who could reach its port could run code in the
container. The token now comes from `JUPYTER_TOKEN` in `.env`; left empty,
JupyterLab generates a random one at start and prints it in its log.
"""

from pathlib import Path

import pytest

yaml = pytest.importorskip("yaml")

REPO = Path(__file__).resolve().parents[1]
COMPOSE = REPO / "docker-compose.yml"


@pytest.fixture(scope="module")
def jupyterlab():
    config = yaml.safe_load(COMPOSE.read_text(encoding="utf-8"))
    return config["services"]["jupyterlab"]


def test_no_fixed_token_anywhere_in_the_service(jupyterlab):
    assert "testing_token" not in str(jupyterlab)


def test_the_token_comes_from_the_environment(jupyterlab):
    assert jupyterlab["environment"]["JUPYTER_TOKEN"] == "${JUPYTER_TOKEN:-}"


def test_the_command_does_not_set_a_token(jupyterlab):
    """A token on the command line would override JUPYTER_TOKEN."""
    assert "token" not in str(jupyterlab.get("command", "")).lower()


def test_example_env_leaves_it_empty():
    lines = (REPO / "example.env").read_text(encoding="utf-8").splitlines()
    assert "JUPYTER_TOKEN=" in lines
    assert not any(
        line.startswith("JUPYTER_TOKEN=") and line != "JUPYTER_TOKEN=" for line in lines
    )
