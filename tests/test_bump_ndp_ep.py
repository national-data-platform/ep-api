"""Each release opens the pull request that installs it from NDP-EP (#400).

``scripts/bump_ndp_ep.py`` rewrites the pin in sci-ndp/NDP-EP's setup.sh;
the release workflow runs it and opens the pull request.
"""

from pathlib import Path

import pytest

from scripts.bump_ndp_ep import NOTHING_TO_DO, main, pinned_release

WORKFLOW = Path(__file__).resolve().parents[1] / ".github/workflows/docker-publish.yml"

# The pin as sci-ndp/NDP-EP's setup.sh writes it (sci-ndp/NDP-EP#17).
SETUP_SH = """#!/usr/bin/env bash
#  Keep the line in this exact form: that pull request rewrites it.
#    EP_VERSION=v0.34.72 bash setup.sh ...
set -euo pipefail

EP_VERSION="${EP_VERSION:-v0.34.73}"
RELEASE="https://github.com/national-data-platform/ep-api/releases/download/${EP_VERSION}"
export EP_REPO_REF="$EP_VERSION"
"""


@pytest.fixture
def setup_sh(tmp_path):
    path = tmp_path / "setup.sh"
    path.write_text(SETUP_SH, encoding="utf-8")
    return path


def test_a_newer_release_raises_only_the_pinned_default(setup_sh):
    assert main(["v0.34.74", str(setup_sh)]) == 0

    text = setup_sh.read_text(encoding="utf-8")
    assert pinned_release(text) == "v0.34.74"
    assert text == SETUP_SH.replace(
        'EP_VERSION="${EP_VERSION:-v0.34.73}"',
        'EP_VERSION="${EP_VERSION:-v0.34.74}"',
    )


def test_a_minor_release_is_newer_than_a_high_patch(setup_sh):
    assert main(["v0.35.0", str(setup_sh)]) == 0
    assert pinned_release(setup_sh.read_text(encoding="utf-8")) == "v0.35.0"


@pytest.mark.parametrize("tag", ["v0.34.73", "v0.34.9", "v0.33.100"])
def test_a_release_not_newer_than_the_pin_changes_nothing(setup_sh, tag):
    assert main([tag, str(setup_sh)]) == NOTHING_TO_DO
    assert setup_sh.read_text(encoding="utf-8") == SETUP_SH


def test_a_prerelease_changes_nothing(setup_sh):
    assert main(["v0.35.0-rc1", str(setup_sh)]) == NOTHING_TO_DO
    assert setup_sh.read_text(encoding="utf-8") == SETUP_SH


@pytest.mark.parametrize("tag", ["0.34.74", "v0.34", "latest"])
def test_a_tag_that_is_not_a_release_is_an_error(setup_sh, tag):
    assert main([tag, str(setup_sh)]) == 1
    assert setup_sh.read_text(encoding="utf-8") == SETUP_SH


@pytest.mark.parametrize(
    "line",
    [
        'EP_VERSION="v0.34.73"',  # the form before sci-ndp/NDP-EP#17
        "EP_VERSION=${EP_VERSION:-v0.34.73}",
        "",
    ],
)
def test_a_setup_sh_without_the_expected_line_is_left_alone(tmp_path, line):
    text = SETUP_SH.replace('EP_VERSION="${EP_VERSION:-v0.34.73}"', line)
    path = tmp_path / "setup.sh"
    path.write_text(text, encoding="utf-8")

    assert main(["v0.34.74", str(path)]) == 1
    assert path.read_text(encoding="utf-8") == text


def test_two_pins_are_left_alone(tmp_path):
    text = SETUP_SH + 'EP_VERSION="${EP_VERSION:-v0.34.70}"\n'
    path = tmp_path / "setup.sh"
    path.write_text(text, encoding="utf-8")

    assert main(["v0.34.74", str(path)]) == 1
    assert path.read_text(encoding="utf-8") == text


def test_the_release_workflow_opens_the_pull_request_after_publishing():
    workflow = WORKFLOW.read_text(encoding="utf-8")
    job = workflow.split("\n  propose-ndp-ep-bump:\n", 1)[1]

    assert "needs: publish" in job
    assert "needs.publish.outputs.prerelease == 'false'" in job
    assert "secrets.NDP_EP_PR_TOKEN" in job
    assert "python3 scripts/bump_ndp_ep.py" in job
    assert "gh pr create --repo sci-ndp/NDP-EP" in job
    publish = workflow.split("\n  propose-ndp-ep-bump:\n", 1)[0]
    assert "prerelease: ${{ steps.meta.outputs.prerelease }}" in publish
    assert "tag: ${{ steps.meta.outputs.tag }}" in publish
