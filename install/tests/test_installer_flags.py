"""
The installer accepts the arguments the platform actually sends (issue #285).

The platform's create-endpoint page builds its command from a deployment
variable whose production value is

    bash <(curl -s .../setup.sh) --config_id

with the id appended, plus ``--env test`` on a test deployment. Those
spellings are not this installer's documented ones, and its parser ends in
``fail "Unknown option"``, so getting them wrong does not degrade the install:
it kills it on the first line.

Each run is stopped at the prerequisite check by a ``docker`` that refuses to
answer. That is deliberate: it is the first thing the installer does after
resolving its arguments, so the run never reaches the network and the test
says the same thing on every machine.
"""

import os
import shutil
import subprocess
from pathlib import Path

import pytest

INSTALLER = Path(__file__).resolve().parents[1] / "install.sh"

PROD = "https://federation.ndp.utah.edu"
TEST = "https://federation.ndp.utah.edu/test"


def _working_bash():
    """
    An absolute path to a bash that actually runs.

    Resolved by name and probed rather than taken on trust: on Windows the
    first ``bash`` on PATH is usually WSL's, which cannot execute a script
    from a Windows checkout, and passing an ``env`` to ``subprocess`` can
    pick it even when ``shutil.which`` reports Git's.
    """
    candidates = [
        shutil.which("bash"),
        r"C:\Program Files\Git\bin\bash.exe",
        r"C:\Program Files\Git\usr\bin\bash.exe",
        "/bin/bash",
        "/usr/bin/bash",
    ]

    for candidate in candidates:
        if not candidate or not os.path.exists(candidate):
            continue
        try:
            probe = subprocess.run(
                [candidate, "-c", "echo ok"],
                capture_output=True,
                text=True,
                timeout=30,
            )
        except OSError:
            continue
        if probe.returncode == 0 and "ok" in probe.stdout:
            return candidate

    return None


BASH = _working_bash()

pytestmark = pytest.mark.skipif(
    BASH is None, reason="no working bash; the installer is a bash script"
)


@pytest.fixture(scope="module")
def stopped_at_docker(tmp_path_factory):
    """A PATH whose docker exists but never answers."""
    stub_dir = tmp_path_factory.mktemp("stub-bin")
    stub = stub_dir / "docker"
    stub.write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
    stub.chmod(0o755)
    return str(stub_dir)


def run(stub_dir, *args):
    """Run the installer and return everything it printed."""
    env = dict(os.environ)
    env["PATH"] = stub_dir + os.pathsep + env.get("PATH", "")

    result = subprocess.run(
        [BASH, str(INSTALLER), *args, "--dry-run"],
        capture_output=True,
        text=True,
        timeout=120,
        env=env,
    )
    return result.stdout + result.stderr


class TestTheSpellingsThePlatformSends:
    """``--config_id`` is what arrives; ``--config-id`` is what was accepted."""

    def test_the_underscore_spelling_is_accepted(self, stopped_at_docker):
        assert "Unknown option" not in run(stopped_at_docker, "--config_id", "FAKE")

    def test_the_documented_spelling_still_works(self, stopped_at_docker):
        assert "Unknown option" not in run(stopped_at_docker, "--config-id", "FAKE")

    def test_the_underscore_federation_url_is_accepted(self, stopped_at_docker):
        output = run(
            stopped_at_docker,
            "--config_id",
            "FAKE",
            "--federation_url",
            "https://custom.example.invalid",
        )

        assert "Unknown option" not in output

    def test_an_option_nobody_sends_is_still_refused(self, stopped_at_docker):
        """The aliases are three names, not an open door."""
        output = run(stopped_at_docker, "--config_id", "FAKE", "--not-an-option")

        assert "Unknown option: --not-an-option" in output

    def test_the_whole_production_command_gets_through(self, stopped_at_docker):
        """The exact shape the platform hands an operator on a test deployment."""
        output = run(stopped_at_docker, "--config_id", "FAKE", "--env", "test")

        assert "Unknown option" not in output
        assert f"Federation: {TEST}" in output


class TestEnvSelectsTheFederation:
    """``--env`` names a Federation; the URL is the installer's business."""

    def test_test_selects_the_test_federation(self, stopped_at_docker):
        assert f"Federation: {TEST}" in run(
            stopped_at_docker, "--config_id", "FAKE", "--env", "test"
        )

    def test_prod_selects_production(self, stopped_at_docker):
        assert f"Federation: {PROD}" in run(
            stopped_at_docker, "--config_id", "FAKE", "--env", "prod"
        )

    def test_without_env_production_is_the_default(self, stopped_at_docker):
        assert f"Federation: {PROD}" in run(stopped_at_docker, "--config_id", "FAKE")

    def test_an_unknown_environment_is_refused_by_name(self, stopped_at_docker):
        """
        Rejected rather than quietly treated as production: an operator who
        meant the test federation must not register against the real one,
        where registering creates a real Keycloak client.
        """
        output = run(stopped_at_docker, "--config_id", "FAKE", "--env", "staging")

        assert "--env must be prod or test" in output
        assert "staging" in output


class TestAnExplicitUrlWins:
    """
    The platform sends both on a test deployment, and the script this
    installer replaces resolved them in this order.
    """

    def test_an_explicit_url_is_not_overruled_by_env(self, stopped_at_docker):
        output = run(
            stopped_at_docker,
            "--config_id",
            "FAKE",
            "--federation_url",
            "https://custom.example.invalid",
            "--env",
            "test",
        )

        assert "Federation: https://custom.example.invalid" in output

    def test_order_on_the_command_line_does_not_matter(self, stopped_at_docker):
        """--env is resolved after parsing, so it cannot depend on position."""
        output = run(
            stopped_at_docker,
            "--config_id",
            "FAKE",
            "--env",
            "test",
            "--federation-url",
            "https://custom.example.invalid",
        )

        assert "Federation: https://custom.example.invalid" in output


class TestTheFederationIsAnnounced:
    """
    Printed before anything happens, which is also what makes --env safe to
    use: the URL it resolved to is on screen rather than implied.
    """

    def test_the_url_is_printed_before_the_prerequisite_check(self, stopped_at_docker):
        output = run(stopped_at_docker, "--config_id", "FAKE")

        assert output.index("Federation:") < output.index("Checking prerequisites")
