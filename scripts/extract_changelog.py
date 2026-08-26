#!/usr/bin/env python3
"""Extract the CHANGELOG section for one version, to use as release notes.

The release is created by the publish workflow rather than by hand, so its notes
have to come from somewhere. CHANGELOG.md already carries them in the house
style, and taking them from there keeps the release page and the changelog from
drifting apart.
"""

import argparse
import re
import sys
from pathlib import Path

DEFAULT_CHANGELOG_PATH = Path("CHANGELOG.md")

# Matches a release heading: "## [0.34.18] - 2026-08-26" (the date is optional,
# and "## [Unreleased]" is matched too so it can be rejected explicitly).
_HEADING_RE = re.compile(r"^##\s+\[([^\]]+)\]", re.MULTILINE)


def normalize_version(version):
    """Strip the leading ``v`` from a tag or version string.

    Parameters
    ----------
    version : str
        Tag or version, e.g. ``v0.34.18`` or ``0.34.18``.

    Returns
    -------
    str
        The bare version string, without surrounding whitespace.
    """
    version = version.strip()
    return version[1:] if version.startswith("v") else version


def extract_section(version, path=DEFAULT_CHANGELOG_PATH):
    """Return the body of the CHANGELOG section for ``version``.

    Parameters
    ----------
    version : str
        Version to look for, with or without a leading ``v``.
    path : pathlib.Path, optional
        The changelog to read.

    Returns
    -------
    str
        Everything between that version's heading and the next one, stripped of
        surrounding blank lines.

    Raises
    ------
    FileNotFoundError
        If ``path`` does not exist.
    ValueError
        If the version has no section, or its section is empty.
    """
    wanted = normalize_version(version)
    text = Path(path).read_text(encoding="utf-8")

    headings = list(_HEADING_RE.finditer(text))
    for index, heading in enumerate(headings):
        if heading.group(1) != wanted:
            continue
        start = heading.end()
        # The section runs to the next release heading, or to the end of file
        # for the oldest entry.
        end = headings[index + 1].start() if index + 1 < len(headings) else len(text)
        # Drop the rest of the heading line (the " - 2026-08-26" date part).
        body = text[start:end].split("\n", 1)[-1].strip()
        if not body:
            raise ValueError(f"the section for {wanted} in {path} is empty")
        return body

    raise ValueError(f"no section for {wanted} found in {path}")


def main(argv=None):
    """Print the release notes for the requested version.

    Returns
    -------
    int
        ``0`` on success, ``2`` when the notes cannot be produced.
    """
    parser = argparse.ArgumentParser(
        description="Print the CHANGELOG section for a version."
    )
    parser.add_argument("version", help="Version to extract, e.g. v0.34.18")
    parser.add_argument(
        "--changelog",
        type=Path,
        default=DEFAULT_CHANGELOG_PATH,
        help="Changelog to read (default: %(default)s)",
    )
    args = parser.parse_args(argv)

    if normalize_version(args.version).lower() == "unreleased":
        print("error: refusing to release the Unreleased section", file=sys.stderr)
        return 2

    try:
        print(extract_section(args.version, args.changelog))
    except (FileNotFoundError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())
