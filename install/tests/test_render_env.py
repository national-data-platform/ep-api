"""
Tests for rendering a deployment .env from example.env.

The behaviour these protect is the reason the module exists: the previous
installer kept its own hardcoded list of settings and fell eleven variables
behind example.env without anything failing.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from render_env import quote, render  # noqa: E402

EXAMPLE = """\
# A comment that must survive
ORGANIZATION=My-Organization
EP_NAME=my_endpoint

# Optional, shown commented out
# OIDC_ISSUER=https://idp.example.org/realms/NDP
# OIDC_CLIENT_ID=ndp-ep-ui

ENABLE_GROUP_BASED_ACCESS=False
GROUP_NAMES=
"""


def test_values_are_replaced():
    text, applied, unknown = render(EXAMPLE, {"ORGANIZATION": "Tarragona"})
    assert "ORGANIZATION=Tarragona" in text
    assert applied == ["ORGANIZATION"]
    assert unknown == []


def test_untouched_variables_keep_their_documented_default():
    text, _, _ = render(EXAMPLE, {"ORGANIZATION": "Tarragona"})
    assert "EP_NAME=my_endpoint" in text
    assert "ENABLE_GROUP_BASED_ACCESS=False" in text


def test_comments_survive():
    text, _, _ = render(EXAMPLE, {"ORGANIZATION": "Tarragona"})
    assert "# A comment that must survive" in text


def test_commented_out_option_is_uncommented_when_set():
    text, applied, _ = render(EXAMPLE, {"OIDC_ISSUER": "https://idp/realms/NDP"})
    assert "OIDC_ISSUER=https://idp/realms/NDP" in text
    assert "# OIDC_ISSUER=https://idp/realms/NDP" not in text
    assert "OIDC_ISSUER" in applied


def test_commented_out_option_stays_commented_when_not_set():
    text, _, _ = render(EXAMPLE, {"ORGANIZATION": "Tarragona"})
    assert "# OIDC_CLIENT_ID=ndp-ep-ui" in text


# This is the regression that motivated the module: a variable added to
# example.env must reach new installations without the installer changing.
def test_a_variable_added_to_the_example_appears_without_installer_changes():
    extended = EXAMPLE + "\nBRAND_NEW_SETTING=default-value\n"
    text, _, _ = render(extended, {"ORGANIZATION": "Tarragona"})
    assert "BRAND_NEW_SETTING=default-value" in text


def test_override_for_an_undocumented_variable_is_reported():
    _, applied, unknown = render(EXAMPLE, {"NOT_A_REAL_SETTING": "x"})
    assert applied == []
    assert unknown == ["NOT_A_REAL_SETTING"]


@pytest.mark.parametrize(
    "value,expected",
    [
        ("simple", "simple"),
        ("", ""),
        ("https://idp.example.org/realms/NDP", "https://idp.example.org/realms/NDP"),
        ("ndp_ep/ep-6a5e300b", "ndp_ep/ep-6a5e300b"),
        ("has space", '"has space"'),
        ('has "quote"', '"has \\"quote\\""'),
    ],
)
def test_quoting_only_when_needed(value, expected):
    # Compose parses this file without a shell, so stray quotes would become
    # part of the value.
    assert quote(value) == expected


def test_real_example_env_renders():
    """The file shipped in the repository must actually render."""
    example_path = Path(__file__).resolve().parents[2] / "example.env"
    text, applied, unknown = render(
        example_path.read_text(encoding="utf-8"),
        {"ORGANIZATION": "Tarragona", "EP_NAME": "tarragona_ep"},
    )
    assert unknown == []
    assert sorted(applied) == ["EP_NAME", "ORGANIZATION"]
    assert "ORGANIZATION=Tarragona" in text


def test_every_variable_the_installer_sets_is_documented():
    """
    Guard against the drift that broke the previous installer: every variable
    install.sh writes must exist in example.env.
    """
    import re

    install_sh = (Path(__file__).resolve().parents[1] / "install.sh").read_text(
        encoding="utf-8"
    )
    example_path = Path(__file__).resolve().parents[2] / "example.env"
    example_text = example_path.read_text(encoding="utf-8")

    documented = set(
        re.findall(r"^#?\s*([A-Z][A-Z0-9_]*)=", example_text, flags=re.MULTILINE)
    )
    set_by_installer = set(re.findall(r"^\s*put ([A-Z][A-Z0-9_]*) ", install_sh, re.M))

    assert set_by_installer, "no 'put' calls found — did install.sh change shape?"
    undocumented = sorted(set_by_installer - documented)
    assert not undocumented, (
        "install.sh sets variables that example.env does not document: "
        f"{undocumented}"
    )
