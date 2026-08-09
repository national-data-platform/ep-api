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


def test_an_endpoint_with_no_local_catalog_renders():
    """
    The lightest install: no catalog, nothing stored locally. Every value it
    writes must be documented in example.env, and the rendered file must say
    plainly that there is no catalog rather than leaving a stale backend.
    """
    example_path = Path(__file__).resolve().parents[2] / "example.env"
    text, applied, unknown = render(
        example_path.read_text(encoding="utf-8"),
        {
            "LOCAL_CATALOG_BACKEND": "none",
            "CKAN_LOCAL_ENABLED": "False",
            "CKAN_URL": "",
            "CKAN_API_KEY": "",
            "MONGODB_CONNECTION_STRING": "",
        },
    )

    assert unknown == []
    assert "LOCAL_CATALOG_BACKEND=none" in text
    assert "CKAN_LOCAL_ENABLED=False" in text
    # Nothing may be left pointing at a MongoDB or CKAN that was not installed.
    assert "MONGODB_CONNECTION_STRING=\n" in text
    assert "CKAN_URL=\n" in text
    assert "CKAN_API_KEY=\n" in text


def test_an_install_without_a_registration_is_not_public():
    """
    IS_PUBLIC is what lets the metrics task post to the Federation. It used to
    be written only when a registration was fetched, so declining to register
    left example.env's demo default of True and the Endpoint reported to a
    platform it had deliberately not joined.

    The installer must switch it off with the rest of the defaults, before the
    registration block gets its chance to turn it back on.
    """
    import re

    install_sh = (Path(__file__).resolve().parents[1] / "install.sh").read_text(
        encoding="utf-8"
    )

    default_off = re.search(r'^\s*put IS_PUBLIC "False"', install_sh, re.M)
    from_registration = re.search(r"^\s*put IS_PUBLIC \"\$\(", install_sh, re.M)

    assert default_off, 'install.sh never sets IS_PUBLIC "False" by default'
    assert from_registration, "install.sh no longer sets IS_PUBLIC from a registration"
    assert default_off.start() < from_registration.start(), (
        "the default must come first, or a registration asking to be listed "
        "would be overridden by it"
    )


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


def test_the_endpoint_is_built_from_the_checkout_being_installed():
    """
    `compose up -d` builds only when no image exists, so on a machine that has
    run an Endpoint before, the container comes back from the image built the
    first time and the checkout is never compiled in. The install then reports
    success while running old code — a route added today answers 404 — and the
    freshly rendered .env makes it look like a configuration problem.
    """
    install_sh = (Path(__file__).resolve().parents[1] / "install.sh").read_text(
        encoding="utf-8"
    )

    # The command is written with ${COMPOSE[@]}, since compose is either
    # `docker compose` or `docker-compose` depending on the machine.
    endpoint_ups = [
        line
        for line in install_sh.splitlines()
        if "up -d" in line and "EP_API_PORT=" in line
    ]

    assert endpoint_ups, "no 'compose up' for the Endpoint found in install.sh"
    for line in endpoint_ups:
        assert (
            "--build" in line
        ), f"the Endpoint is started without --build: {line.strip()}"


def test_access_requests_bring_their_own_mongodb():
    """
    Access requests are stored in MongoDB, read through
    MONGODB_CONNECTION_STRING, whatever the catalog backend is. Offering the
    option without standing up a MongoDB — which is what the setting had
    before, documented and unreachable — produces an Endpoint that accepts the
    answer and then cannot serve the feature.

    So enabling it must add the compose profile and a connection string on any
    backend that does not already provide one.
    """
    install_sh = (Path(__file__).resolve().parents[1] / "install.sh").read_text(
        encoding="utf-8"
    )

    assert (
        'ask_yes_no want_access_requests "Enable access requests?"' in install_sh
    ), "the installer never offers access requests"
    assert "--access-requests)" in install_sh, "there is no flag for an unattended run"

    block_start = install_sh.index('if [[ "$want_access_requests" == "yes" ]]; then')
    block = install_sh[block_start : install_sh.index("\nfi\n", block_start)]

    assert 'put ENABLE_ACCESS_REQUESTS "True"' in block
    assert (
        'profiles+=("mongodb")' in block
    ), "no MongoDB is installed for a backend that does not provide one"
    assert (
        "put MONGODB_CONNECTION_STRING " in block
    ), "the MongoDB installed for access requests is never pointed at"


def test_starting_mongodb_does_not_publish_a_database_console():
    """
    mongo-express exposes the whole database, with the demo credentials that
    are the same in every deployment. It shared the `mongodb` profile, so
    choosing MongoDB as the catalog — or, now, enabling access requests on an
    Endpoint that has no MongoDB — published an admin console on 8082 that
    nobody asked for.
    """
    compose = (Path(__file__).resolve().parents[2] / "docker-compose.yml").read_text(
        encoding="utf-8"
    )

    block = compose[compose.index("mongo-express:") :]
    profiles_line = next(
        line for line in block.splitlines() if line.strip().startswith("profiles:")
    )

    assert "mongodb" not in profiles_line, (
        "mongo-express starts with the mongodb profile, so a MongoDB cannot be "
        f"started without it: {profiles_line.strip()}"
    )
    assert "mongo-express" in profiles_line, "mongo-express has no profile of its own"


def test_a_registration_supplies_the_staging_organization():
    """
    A promoted dataset keeps its local organization unless
    PRE_CKAN_ORGANIZATION says otherwise, and the staging credentials cannot
    write to 'services' or to any organization local to the Endpoint. Without
    this the staging catalog looks configured and every publish fails with an
    authorization error naming a user, which reads as a credentials problem.

    The organization is the one the Federation minted the token for, which is
    derived from the configuration id the installer already has.
    """
    install_sh = (Path(__file__).resolve().parents[1] / "install.sh").read_text(
        encoding="utf-8"
    )

    assert (
        'put PRE_CKAN_ORGANIZATION "ep-${config_id}"' in install_sh
    ), "the staging organization is not derived from the registration"
    assert "organization_list_for_user" in install_sh, (
        "nothing checks that the staging catalog accepts that organization "
        "before the configuration is written"
    )
