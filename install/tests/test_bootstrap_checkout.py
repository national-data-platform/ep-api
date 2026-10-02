"""
Re-running the installer must not silently reinstall the previous version.

When it finds a checkout it made earlier, the installer updates it instead of
cloning again. Both commands that were supposed to do the moving failed — a
shallow fetch of a tag leaves it in FETCH_HEAD without writing `refs/tags/`,
and `origin/<tag>` never existed, that namespace being for branches — and
`|| true` hid both, so the run carried on against whatever was already there
(issue #295).

That is how #293 looked unfixed after it had been fixed and released: the
second run reused the first run's checkout.

Exercising this needs git, a network and a repository with two tags in it, so
these pin the shape instead. The bug was one word (`origin/`) and one
swallowed failure, which is exactly what a reader would reinstate while
tidying.
"""

import re
from pathlib import Path

INSTALLER = Path(__file__).resolve().parents[1] / "install.sh"


def bootstrap():
    """The block that materialises the repository, before anything else."""
    body = INSTALLER.read_text(encoding="utf-8")
    start = body.index("Reusing existing checkout")
    end = body.index("Running the installer from")
    return body[start:end]


def test_what_was_fetched_is_what_is_checked_out():
    """
    FETCH_HEAD is the only name that works for a tag and a branch alike after
    an explicit fetch.
    """
    assert "FETCH_HEAD" in bootstrap()


def test_the_remote_branch_namespace_is_not_used_for_the_ref():
    """`origin/<tag>` resolves to nothing; it could never have worked."""
    assert not re.search(r"origin/\$\{?repo_ref", bootstrap())


def test_a_failed_update_is_not_swallowed():
    """
    The failure was invisible, which is what made it expensive: an operator
    saw a successful install of the wrong version.

    Comments are skipped, since the one above the fix quotes the construct it
    describes.
    """
    code = [
        line for line in bootstrap().splitlines() if not line.lstrip().startswith("#")
    ]

    assert "|| true" not in "\n".join(code)


def test_a_checkout_that_cannot_be_moved_is_replaced():
    """Carrying on with it is how the stale version got reinstalled."""
    block = bootstrap()

    assert 'rm -rf "$target"' in block


def test_the_clone_still_happens_when_there_is_nothing_to_reuse():
    body = INSTALLER.read_text(encoding="utf-8")

    assert "git clone --depth 1 --branch" in body
