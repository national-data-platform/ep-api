"""
The answers a Federation configuration can remember for an Endpoint.

A registration records eleven things, none of them the catalog, object
storage, access requests or the ports. Those answers lived only in the local
``.env.install-state``, so reinstalling on another machine meant answering
from memory. ``sci-ndp/ndp-federation#100`` added a free-form settings object
under the configuration id to hold them.

This module is the translation in both directions, and it is a module rather
than a heredoc inside ``install.sh`` for the same reason ``render_env.py`` is:
so it can be tested without a terminal, a Federation or a Docker daemon.

Nothing here talks to the network. The installer does the HTTP; this decides
what travels and what comes back.
"""

import json
import sys

# The answers worth remembering: what the installer asks and the Federation
# does not already record.
#
# Credentials are deliberately absent, and must stay absent. They are not
# answers worth reusing, and an Endpoint's own secrets have no business
# travelling to a service that has no use for them. That includes the CKAN
# and S3 keys, which the installer asks for in the same breath as the
# settings below.
REMEMBERED_KEYS = (
    "backend",
    "want_s3",
    "s3_endpoint",
    "s3_secure",
    "ep_api_port",
    "auth_api_url",
    "want_access_requests",
    "mongodb_url",
    "ckan_url",
)


def to_payload(values):
    """
    Build the body of a settings write.

    Parameters
    ----------
    values : dict
        Answers keyed by the names in ``REMEMBERED_KEYS``. Unknown keys are
        dropped rather than sent, so a caller cannot smuggle a credential
        through by naming it something else.

    Returns
    -------
    str
        A JSON object shaped ``{"settings": {...}}``.
    """
    remembered = {}

    for key in REMEMBERED_KEYS:
        value = values.get(key)
        if value is None:
            continue
        remembered[key] = str(value)

    return json.dumps({"settings": remembered})


def from_payload(body):
    """
    Read a settings response into the answers the installer understands.

    Parameters
    ----------
    body : str
        The response from the Federation, or anything at all: a body that is
        not the expected shape yields no answers rather than raising, because
        failing to read remembered answers must not stop an installation.

    Returns
    -------
    dict
        Known keys with a non-empty value. A key the Federation holds but
        this version does not know is ignored here and left untouched there,
        so an Endpoint that stored more than this installer understands does
        not lose it.
    """
    try:
        stored = json.loads(body).get("settings")
    except (TypeError, ValueError, AttributeError):
        return {}

    if not isinstance(stored, dict):
        return {}

    answers = {}

    for key in REMEMBERED_KEYS:
        value = stored.get(key)
        # An empty string is a stored "unset" and must not override a
        # default; False and 0 are answers and must survive.
        if value is None or value == "":
            continue
        answers[key] = str(value)

    return answers


def _shell_quote(value):
    """Quote a value so a shell reads it as one literal word."""
    return "'" + value.replace("'", "'\\''") + "'"


def as_shell_assignments(answers):
    """Render answers as shell assignments for the installer to eval."""
    return "\n".join(
        "%s=%s" % (key, _shell_quote(value))
        for key, value in answers.items()
        if key in REMEMBERED_KEYS
    )


def main(argv):
    """
    ``load`` turns a response body into shell assignments; ``save`` turns
    ``key=value`` arguments into a request body.
    """
    if len(argv) < 2:
        print("usage: remembered_settings.py load|save ...", file=sys.stderr)
        return 2

    action = argv[1]

    if action == "load":
        body = argv[2] if len(argv) > 2 else ""
        print(as_shell_assignments(from_payload(body)))
        return 0

    if action == "save":
        values = {}
        for pair in argv[2:]:
            key, _, value = pair.partition("=")
            values[key] = value
        print(to_payload(values))
        return 0

    print("unknown action: %s" % action, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
