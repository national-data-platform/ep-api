"""Tests for the installer published with each release (issue #373)."""

import hashlib
import re
from pathlib import Path

import pytest

from scripts.build_installer_asset import build, main

REPO = Path(__file__).resolve().parents[1]
INSTALLER = REPO / "install" / "install.sh"
WORKFLOW = REPO / ".github" / "workflows" / "docker-publish.yml"


def test_the_asset_installs_its_own_release(tmp_path):
    """Run from the release, it clones that release, not whatever is latest."""
    build("v1.2.3", tmp_path, installer=INSTALLER)

    asset = (tmp_path / "install.sh").read_text(encoding="utf-8")
    assert 'INSTALLER_RELEASE="v1.2.3"' in asset
    assert asset.count('INSTALLER_RELEASE="') == 1


def test_the_rest_of_the_installer_is_unchanged(tmp_path):
    build("v1.2.3", tmp_path, installer=INSTALLER)

    original = INSTALLER.read_text(encoding="utf-8").splitlines()
    asset = (tmp_path / "install.sh").read_text(encoding="utf-8").splitlines()
    different = [pair for pair in zip(original, asset) if pair[0] != pair[1]]
    assert len(original) == len(asset)
    assert different == [('INSTALLER_RELEASE=""', 'INSTALLER_RELEASE="v1.2.3"')]


def test_sha256sums_matches_the_asset(tmp_path):
    build("v1.2.3", tmp_path, installer=INSTALLER)

    digest = hashlib.sha256((tmp_path / "install.sh").read_bytes()).hexdigest()
    assert (tmp_path / "SHA256SUMS").read_text() == f"{digest}  install.sh\n"


def test_the_asset_is_executable(tmp_path):
    build("v1.2.3", tmp_path, installer=INSTALLER)

    assert (tmp_path / "install.sh").stat().st_mode & 0o111


@pytest.mark.parametrize("tag", ["1.2.3", "v1.2", "main", "v1.2.3; rm -rf /", ""])
def test_only_a_release_tag_is_embedded(tmp_path, tag):
    with pytest.raises(ValueError):
        build(tag, tmp_path, installer=INSTALLER)


def test_a_prerelease_tag_is_accepted(tmp_path):
    build("v1.3.0-rc1", tmp_path, installer=INSTALLER)

    assert 'INSTALLER_RELEASE="v1.3.0-rc1"' in (tmp_path / "install.sh").read_text()


def test_an_installer_without_the_marker_is_refused(tmp_path):
    """A rename must fail the release, not ship an asset that tracks latest."""
    fake = tmp_path / "install.sh.src"
    fake.write_text("#!/bin/bash\necho hi\n", encoding="utf-8")

    with pytest.raises(ValueError):
        build("v1.2.3", tmp_path / "out", installer=fake)


def test_the_command_line(tmp_path, capsys):
    assert main(["v1.2.3", str(tmp_path), "--installer", str(INSTALLER)]) == 0
    assert (tmp_path / "SHA256SUMS").exists()


def test_the_release_workflow_publishes_them():
    text = WORKFLOW.read_text(encoding="utf-8")

    assert "scripts/build_installer_asset.py" in text
    upload = re.search(r"gh release upload .*--clobber", text)
    assert upload, "the assets are never attached to the release"
    assert text.index("gh release create") < text.index("gh release upload")
