#!/usr/bin/env python3
"""Check that a release tag agrees with the version the API reports.

The image published to Docker Hub and the API running inside it must never
disagree about which version they are. ``swagger_version`` is surfaced at
``/status/``, in ``/docs`` and in the periodic metrics payload, so a tag that
does not match it silently misreports every deployment built from that release.
Running this before the image is built turns that into a failed workflow
instead.
"""

import argparse
import re
import sys
from pathlib import Path

DEFAULT_SETTINGS_PATH = Path("api/config/swagger_settings.py")

# Matches the declaration: swagger_version: str = "0.34.17"
_VERSION_RE = re.compile(
    r"""^\s*swagger_version\s*:\s*str\s*=\s*["']([^"']+)["']""",
    re.MULTILINE,
)


def normalize_tag(tag):
    """Strip the leading ``v`` from a release tag.

    Parameters
    ----------
    tag : str
        Release tag as GitHub reports it, e.g. ``v0.34.17`` or ``0.34.17``.

    Returns
    -------
    str
        The bare version string, without surrounding whitespace.
    """
    tag = tag.strip()
    # Only one leading "v" is removed. `lstrip("v")` would strip every leading
    # "v" and turn a tag like "vv1" into "1".
    return tag[1:] if tag.startswith("v") else tag


def read_swagger_version(path=DEFAULT_SETTINGS_PATH):
    """Read ``swagger_version`` out of the settings module.

    The value is parsed with a regular expression rather than imported, so the
    check runs without installing the API's dependencies.

    Parameters
    ----------
    path : pathlib.Path, optional
        Path to the module declaring ``swagger_version``.

    Returns
    -------
    str
        The declared version.

    Raises
    ------
    FileNotFoundError
        If ``path`` does not exist.
    ValueError
        If no ``swagger_version`` declaration is found.
    """
    text = Path(path).read_text(encoding="utf-8")
    match = _VERSION_RE.search(text)
    if match is None:
        raise ValueError(f"no swagger_version declaration found in {path}")
    return match.group(1)


def main(argv=None):
    """Compare the given release tag against the declared version.

    Returns
    -------
    int
        ``0`` when they agree, ``1`` on a mismatch, ``2`` when the declared
        version cannot be read at all.
    """
    parser = argparse.ArgumentParser(
        description="Check that a release tag matches swagger_version."
    )
    parser.add_argument("tag", help="Release tag being published, e.g. v0.34.17")
    parser.add_argument(
        "--settings",
        type=Path,
        default=DEFAULT_SETTINGS_PATH,
        help="Module declaring swagger_version (default: %(default)s)",
    )
    args = parser.parse_args(argv)

    try:
        declared = read_swagger_version(args.settings)
    except (FileNotFoundError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    version = normalize_tag(args.tag)
    if version != declared:
        print(
            f"error: release tag '{args.tag}' does not match swagger_version "
            f"'{declared}' in {args.settings}. Bump swagger_version and the "
            f"CHANGELOG, or retag the release.",
            file=sys.stderr,
        )
        return 1

    print(f"Release tag and swagger_version agree on {declared}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
