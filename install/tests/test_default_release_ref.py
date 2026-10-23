"""
Installed from the web, the installer runs the latest release, not ``main``
(issue #371).

``bash <(curl …/install.sh)`` clones the repository and re-runs itself from the
clone. It cloned ``main``, so the same command installed a different program
from one week to the next, and a bad push to ``main`` reached every new
installation at once. It now resolves the newest release tag (``vX.Y.Z``, no
pre-releases) and clones that; ``--ref <tag|branch>`` or ``EP_REPO_REF`` choose
another, the flag winning. What was installed is recorded in the install state.

A local repository with three releases, a pre-release and newer commits on
``main`` stands in for GitHub. Each version's ``install.sh`` only says which
version it is, so nothing is installed.
"""

import os
import shutil
import subprocess
from pathlib import Path

import pytest

INSTALLER = Path(__file__).resolve().parents[1] / "install.sh"
BASH = shutil.which("bash")
GIT = shutil.which("git")

pytestmark = pytest.mark.skipif(
    BASH is None or GIT is None or os.name == "nt", reason="needs bash and git"
)


def _git(cwd, *args):
    subprocess.run(
        [GIT, *args],
        cwd=cwd,
        check=True,
        capture_output=True,
        env={
            **os.environ,
            "GIT_AUTHOR_NAME": "t",
            "GIT_AUTHOR_EMAIL": "t@example.invalid",
            "GIT_COMMITTER_NAME": "t",
            "GIT_COMMITTER_EMAIL": "t@example.invalid",
        },
    )


def _commit(repo, label):
    (repo / "install").mkdir(exist_ok=True)
    (repo / "example.env").write_text("X=1\n", encoding="utf-8")
    (repo / "install" / "install.sh").write_text(
        f'#!/bin/bash\necho "RAN {label} $*"\n', encoding="utf-8"
    )
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", label)


@pytest.fixture
def remote(tmp_path):
    """A repository with v0.9.0, v0.10.0, v0.11.0-rc1 and main ahead of them."""
    repo = tmp_path / "upstream"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    for label in ("v0.9.0", "v0.10.0", "v0.11.0-rc1"):
        _commit(repo, label)
        _git(repo, "tag", label)
    _commit(repo, "main")
    return repo


def _bootstrap(tmp_path, remote, *args, ref=None):
    """Run the installer the way a piped run does: with no checkout around it."""
    lone = tmp_path / "piped" / "install.sh"
    lone.parent.mkdir(exist_ok=True)
    shutil.copy(INSTALLER, lone)
    env = {
        **os.environ,
        "EP_REPO_URL": str(remote),
        "EP_INSTALL_DIR": str(tmp_path / "ndp-ep"),
    }
    env.pop("EP_REPO_REF", None)
    if ref is not None:
        env["EP_REPO_REF"] = ref
    return subprocess.run(
        [BASH, str(lone), *args],
        capture_output=True,
        text=True,
        timeout=120,
        env=env,
        stdin=subprocess.DEVNULL,
    )


def test_the_latest_release_is_installed_by_default(tmp_path, remote):
    result = _bootstrap(tmp_path, remote, "--yes")

    assert result.returncode == 0, result.stdout + result.stderr
    assert "RAN v0.10.0" in result.stdout


def test_versions_are_compared_as_versions_not_text(tmp_path, remote):
    """v0.10.0 is newer than v0.9.0, though "0.9" sorts after "0.1" as text."""
    result = _bootstrap(tmp_path, remote)

    assert "RAN v0.9.0" not in result.stdout
    assert "RAN v0.10.0" in result.stdout


def test_a_pre_release_is_not_the_default(tmp_path, remote):
    result = _bootstrap(tmp_path, remote)

    assert "RAN v0.11.0-rc1" not in result.stdout


def test_the_resolved_ref_is_printed(tmp_path, remote):
    result = _bootstrap(tmp_path, remote)

    assert "Installer version: v0.10.0 (latest release)" in result.stdout


def test_ref_picks_a_branch(tmp_path, remote):
    result = _bootstrap(tmp_path, remote, "--ref", "main")

    assert "RAN main" in result.stdout
    assert "Installer version: main" in result.stdout


def test_ref_picks_an_older_release(tmp_path, remote):
    result = _bootstrap(tmp_path, remote, "--ref", "v0.9.0")

    assert "RAN v0.9.0" in result.stdout


def test_the_environment_variable_still_works(tmp_path, remote):
    """It is what the platform's setup.sh sets to pin a version."""
    result = _bootstrap(tmp_path, remote, ref="v0.9.0")

    assert "RAN v0.9.0" in result.stdout


def test_the_flag_wins_over_the_environment(tmp_path, remote):
    result = _bootstrap(tmp_path, remote, "--ref", "main", ref="v0.9.0")

    assert "RAN main" in result.stdout


def test_the_arguments_reach_the_cloned_installer(tmp_path, remote):
    result = _bootstrap(tmp_path, remote, "--ref", "v0.9.0", "--backend", "none")

    assert "RAN v0.9.0 --ref v0.9.0 --backend none" in result.stdout


def test_a_rerun_moves_the_checkout_to_the_new_latest(tmp_path, remote):
    _bootstrap(tmp_path, remote, "--ref", "v0.9.0")
    result = _bootstrap(tmp_path, remote)

    assert "Reusing existing checkout" in result.stdout
    assert "RAN v0.10.0" in result.stdout


def test_without_releases_it_falls_back_to_main_and_says_so(tmp_path):
    repo = tmp_path / "untagged"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    _commit(repo, "main")

    result = _bootstrap(tmp_path, repo)

    assert "RAN main" in result.stdout
    assert "no release" in result.stderr


def test_an_unreachable_repository_stops_with_a_message(tmp_path):
    result = _bootstrap(tmp_path, tmp_path / "does-not-exist")

    assert result.returncode != 0
    assert "Could not list the releases" in result.stderr
    assert "--ref" in result.stderr


def _asset(tmp_path, tag):
    """The installer as a release publishes it (scripts/build_installer_asset.py)."""
    import sys

    sys.path.insert(0, str(INSTALLER.parents[1]))
    from scripts.build_installer_asset import build

    out = tmp_path / "release-asset"
    build(tag, out, installer=INSTALLER)
    return out / "install.sh"


def test_a_release_asset_installs_its_own_release(tmp_path, remote):
    """Downloaded from v0.9.0, it installs v0.9.0 though v0.10.0 is newer."""
    asset = _asset(tmp_path, "v0.9.0")
    env = {
        **os.environ,
        "EP_REPO_URL": str(remote),
        "EP_INSTALL_DIR": str(tmp_path / "ndp-ep"),
    }
    env.pop("EP_REPO_REF", None)

    result = subprocess.run(
        [BASH, str(asset)], capture_output=True, text=True, timeout=120, env=env
    )

    assert "RAN v0.9.0" in result.stdout, result.stdout + result.stderr
    assert "the release this installer came from" in result.stdout


def test_ref_still_chooses_over_the_embedded_release(tmp_path, remote):
    asset = _asset(tmp_path, "v0.9.0")
    env = {
        **os.environ,
        "EP_REPO_URL": str(remote),
        "EP_INSTALL_DIR": str(tmp_path / "ndp-ep"),
    }
    env.pop("EP_REPO_REF", None)

    result = subprocess.run(
        [BASH, str(asset), "--ref", "main"],
        capture_output=True,
        text=True,
        timeout=120,
        env=env,
    )

    assert "RAN main" in result.stdout


def test_the_installed_version_is_recorded(tmp_path):
    """The install state says which installer ran (for support and status)."""
    root = tmp_path / "ep-api"
    shutil.copytree(INSTALLER.parents[1] / "install", root / "install")
    for name in ("example.env", "docker-compose.yml"):
        shutil.copy(INSTALLER.parents[1] / name, root / name)
    _git(root, "init", "-q", "-b", "main")
    _git(root, "add", "-A")
    _git(root, "commit", "-qm", "release")
    _git(root, "tag", "v1.2.3")
    stubs = tmp_path / "bin"
    stubs.mkdir()
    (stubs / "docker").write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    (stubs / "docker").chmod(0o755)

    result = subprocess.run(
        [
            BASH,
            str(root / "install" / "install.sh"),
            "--backend",
            "none",
            "--no-netbird",
            "--yes",
            "--no-start",
        ],
        capture_output=True,
        text=True,
        timeout=120,
        env={**os.environ, "PATH": f"{stubs}{os.pathsep}{os.environ['PATH']}"},
        stdin=subprocess.DEVNULL,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    state = (root / ".env.install-state").read_text(encoding="utf-8")
    assert "INSTALLER_VERSION=v1.2.3" in state.splitlines()
    import hashlib

    digest = hashlib.sha256((root / "install" / "install.sh").read_bytes()).hexdigest()
    assert f"INSTALLER_SHA256={digest}" in state.splitlines()
