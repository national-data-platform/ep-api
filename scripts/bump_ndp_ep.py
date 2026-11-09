#!/usr/bin/env python3
"""Raise the ep-api release that sci-ndp/NDP-EP's setup.sh installs.

New Endpoints install the release named by one line of NDP-EP's ``setup.sh``::

    EP_VERSION="${EP_VERSION:-v0.34.73}"

The release workflow runs this on a clone of NDP-EP and, when the line
changed, opens a pull request with it (issue #400, sci-ndp/NDP-EP#16).
Merging that pull request is what makes new installations use the release.

Exit codes:

- 0: the line was raised to the new release;
- 10: nothing to do: a prerelease, or a release not newer than the pinned one;
- 1: the tag or the file is not what was expected.
"""

import argparse
import re
import sys
from pathlib import Path

NOTHING_TO_DO = 10

_PIN_RE = re.compile(
    r'^EP_VERSION="\$\{EP_VERSION:-(?P<tag>v[^"}]+)\}"$',
    re.MULTILINE,
)
_RELEASE_RE = re.compile(r"^v(\d+)\.(\d+)\.(\d+)$")


def release_number(tag):
    """Return a release tag as a tuple of integers, for comparing.

    Parameters
    ----------
    tag : str
        A release tag, e.g. ``v0.34.73``.

    Returns
    -------
    tuple of int or None
        ``(0, 34, 73)``, or None for anything that is not a plain
        ``vMAJOR.MINOR.PATCH`` release (a prerelease such as ``v0.35.0-rc1``
        included).
    """
    match = _RELEASE_RE.match(tag)
    if not match:
        return None
    return tuple(int(part) for part in match.groups())


def pinned_release(text):
    """Return the release a setup.sh installs by default.

    Parameters
    ----------
    text : str
        Contents of NDP-EP's ``setup.sh``.

    Returns
    -------
    str or None
        The pinned tag, or None when the file has no ``EP_VERSION`` line in
        the expected form, or more than one.
    """
    found = _PIN_RE.findall(text)
    if len(found) != 1:
        return None
    return found[0]


def raise_pin(text, tag):
    """Return ``text`` with the pinned release replaced by ``tag``."""
    return _PIN_RE.sub(f'EP_VERSION="${{EP_VERSION:-{tag}}}"', text, count=1)


def main(argv=None):
    """Raise the pin in a setup.sh file, and say what happened."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("tag", help="the new release, e.g. v0.34.74")
    parser.add_argument("setup_sh", type=Path, help="path to NDP-EP's setup.sh")
    args = parser.parse_args(argv)

    tag = args.tag.strip()
    if "-" in tag:
        print(f"{tag} is a prerelease; NDP-EP keeps its pin.")
        return NOTHING_TO_DO
    new = release_number(tag)
    if new is None:
        print(f"{tag!r} is not a release tag like v0.34.74.", file=sys.stderr)
        return 1

    text = args.setup_sh.read_text(encoding="utf-8")
    current = pinned_release(text)
    if current is None:
        print(
            f"{args.setup_sh} has no single line of the form "
            'EP_VERSION="${EP_VERSION:-vX.Y.Z}"; not changing it.',
            file=sys.stderr,
        )
        return 1
    if release_number(current) is not None and new <= release_number(current):
        print(f"NDP-EP already installs {current}; {tag} is not newer.")
        return NOTHING_TO_DO

    args.setup_sh.write_text(raise_pin(text, tag), encoding="utf-8")
    print(f"NDP-EP setup.sh: {current} -> {tag}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
