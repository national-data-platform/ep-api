#!/usr/bin/env python3
"""Build the installer published with a release, and its checksum.

The documented way to install was ``bash <(curl …/main/install/install.sh)``:
an unversioned URL, with nothing to verify the bytes against (issue #373).
Each release now carries ``install.sh`` and ``SHA256SUMS`` as assets, so an
operator can download the installer of one version, check it with
``sha256sum -c SHA256SUMS`` and run it.

The asset is ``install/install.sh`` with one line changed: ``INSTALLER_RELEASE``
names the release, so the asset clones that release rather than the newest one
(``--ref`` and ``EP_REPO_REF`` still choose another). Everything else is the
file as tagged.
"""

import argparse
import hashlib
import re
import sys
from pathlib import Path

DEFAULT_INSTALLER = Path("install/install.sh")
MARKER = 'INSTALLER_RELEASE=""'
_TAG_RE = re.compile(r"^v[0-9]+\.[0-9]+\.[0-9]+(-[0-9A-Za-z.]+)?$")


def build(tag, out_dir, installer=DEFAULT_INSTALLER):
    """Write ``install.sh`` and ``SHA256SUMS`` for ``tag`` into ``out_dir``.

    Parameters
    ----------
    tag : str
        The release tag, e.g. ``v0.34.64``.
    out_dir : str or Path
        Directory to write the two files into; created if missing.
    installer : str or Path
        The installer to publish.

    Returns
    -------
    str
        The SHA-256 of the published ``install.sh``.

    Raises
    ------
    ValueError
        When the tag is not a release tag, or the installer does not carry the
        ``INSTALLER_RELEASE`` line exactly once.
    """
    if not _TAG_RE.match(tag or ""):
        raise ValueError(f"not a release tag: {tag!r}")
    lines = Path(installer).read_text(encoding="utf-8").splitlines(keepends=True)
    hits = [i for i, line in enumerate(lines) if line.rstrip("\n") == MARKER]
    if len(hits) != 1:
        raise ValueError(
            f"{installer} must contain the line {MARKER} exactly once "
            f"(found {len(hits)})"
        )
    lines[hits[0]] = f'INSTALLER_RELEASE="{tag}"\n'

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    asset = out / "install.sh"
    asset.write_text("".join(lines), encoding="utf-8")
    asset.chmod(0o755)
    digest = hashlib.sha256(asset.read_bytes()).hexdigest()
    (out / "SHA256SUMS").write_text(f"{digest}  install.sh\n", encoding="utf-8")
    return digest


def main(argv=None):
    """Command-line entry point; returns the process exit code."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("tag", help="release tag, e.g. v0.34.64")
    parser.add_argument("out_dir", help="where to write install.sh and SHA256SUMS")
    parser.add_argument("--installer", default=str(DEFAULT_INSTALLER))
    args = parser.parse_args(argv)
    try:
        digest = build(args.tag, args.out_dir, installer=args.installer)
    except ValueError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    print(f"{digest}  install.sh ({args.tag})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
