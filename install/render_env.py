#!/usr/bin/env python3
"""
Render a deployment ``.env`` from ``example.env`` plus a set of overrides.

``example.env`` is the single source of truth for which variables exist, what
they default to and what they mean. Rendering from it means a variable added
there shows up in every new installation without the installer being touched
— the previous installer kept its own hardcoded list, which had silently
fallen eleven variables behind.

Lines are preserved as-is unless an override applies, so the comments that
document each setting survive into the generated file. A variable that is
commented out in ``example.env`` (an optional setting shown as an example) is
uncommented when an override supplies a value, and left alone otherwise.

Usage:
    render_env.py --example example.env --overrides overrides.json [--output .env]
"""

import argparse
import json
import re
import sys

# Matches both `KEY=value` and a commented-out `# KEY=value` example line.
ASSIGNMENT = re.compile(r"^(?P<comment>#\s*)?(?P<key>[A-Z][A-Z0-9_]*)=(?P<value>.*)$")


def quote(value):
    """
    Quote a value only when it needs it.

    Docker Compose reads this file without a shell, so quotes would otherwise
    end up as part of the value.
    """
    text = "" if value is None else str(value)
    if text == "" or re.fullmatch(r"[A-Za-z0-9_./:@,+-]*", text):
        return text
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'


def render(example_text, overrides):
    """
    Render the file text, applying overrides.

    Returns (text, applied, unknown) where `applied` are the override keys that
    matched a variable in the example, and `unknown` are the ones that did not.
    An unknown key means the installer is trying to set something the Endpoint
    does not document — worth reporting rather than silently writing.
    """
    applied = set()
    out = []

    for line in example_text.splitlines():
        match = ASSIGNMENT.match(line)
        if not match:
            out.append(line)
            continue

        key = match.group("key")
        if key not in overrides:
            out.append(line)
            continue

        # An override always produces a real (uncommented) assignment, even if
        # the example had it commented out as an optional setting.
        out.append(f"{key}={quote(overrides[key])}")
        applied.add(key)

    unknown = sorted(set(overrides) - applied)
    return "\n".join(out) + "\n", sorted(applied), unknown


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--example", required=True)
    parser.add_argument("--overrides", required=True, help="JSON file of KEY -> value")
    parser.add_argument("--output", help="defaults to stdout")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="fail if an override does not correspond to a documented variable",
    )
    args = parser.parse_args(argv)

    with open(args.example, encoding="utf-8") as handle:
        example_text = handle.read()
    with open(args.overrides, encoding="utf-8") as handle:
        overrides = json.load(handle)

    text, applied, unknown = render(example_text, overrides)

    if unknown:
        print(
            "warning: not documented in example.env: " + ", ".join(unknown),
            file=sys.stderr,
        )
        if args.strict:
            return 1

    if args.output:
        with open(args.output, "w", encoding="utf-8") as handle:
            handle.write(text)
        print(f"wrote {args.output} ({len(applied)} values set)", file=sys.stderr)
    else:
        sys.stdout.write(text)

    return 0


if __name__ == "__main__":
    sys.exit(main())
