"""Tests for extracting release notes out of CHANGELOG.md."""

import pytest

from scripts.extract_changelog import (
    extract_section,
    main,
    normalize_version,
)

CHANGELOG = """# Changelog

Some preamble.

## [Unreleased]

## [0.34.18] - 2026-08-26

### Added
- A new thing.

### Backwards compatibility
- Nothing breaks.

## [0.34.17] - 2026-08-17

### Fixed
- An older thing.

## [0.34.16]

### Added
- The oldest entry, with no date.
"""


@pytest.fixture
def changelog(tmp_path):
    """Write a changelog with a known shape and return its path."""
    path = tmp_path / "CHANGELOG.md"
    path.write_text(CHANGELOG, encoding="utf-8")
    return path


class TestNormalizeVersion:
    def test_strips_a_leading_v(self):
        assert normalize_version("v0.34.18") == "0.34.18"

    def test_leaves_a_bare_version_untouched(self):
        assert normalize_version("0.34.18") == "0.34.18"

    def test_strips_surrounding_whitespace(self):
        assert normalize_version("  v1.0.0\n") == "1.0.0"


class TestExtractSection:
    def test_returns_only_that_version(self, changelog):
        body = extract_section("0.34.18", changelog)
        assert "A new thing." in body
        assert "An older thing." not in body

    def test_accepts_a_v_prefixed_tag(self, changelog):
        assert extract_section("v0.34.18", changelog) == extract_section(
            "0.34.18", changelog
        )

    def test_keeps_the_subsection_headings(self, changelog):
        body = extract_section("0.34.18", changelog)
        assert "### Added" in body
        assert "### Backwards compatibility" in body

    def test_drops_the_heading_and_its_date(self, changelog):
        body = extract_section("0.34.18", changelog)
        assert "2026-08-26" not in body
        assert not body.startswith("## [")
        assert "[0.34.18]" not in body

    def test_reads_the_last_section_to_end_of_file(self, changelog):
        body = extract_section("0.34.16", changelog)
        assert "The oldest entry" in body

    def test_raises_for_an_unknown_version(self, changelog):
        with pytest.raises(ValueError, match="no section for 9.9.9"):
            extract_section("9.9.9", changelog)

    def test_raises_for_an_empty_section(self, changelog):
        # "Unreleased" is present but carries no body.
        with pytest.raises(ValueError, match="is empty"):
            extract_section("Unreleased", changelog)

    def test_raises_when_the_file_is_missing(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            extract_section("1.0.0", tmp_path / "nope.md")

    def test_reads_the_repository_changelog(self):
        # The real file must stay parseable, or every release would fail.
        assert "###" in extract_section("0.34.18")


class TestMain:
    def test_prints_the_section(self, changelog, capsys):
        assert main(["v0.34.18", "--changelog", str(changelog)]) == 0
        assert "A new thing." in capsys.readouterr().out

    def test_refuses_to_release_unreleased(self, changelog, capsys):
        assert main(["Unreleased", "--changelog", str(changelog)]) == 2
        assert "refusing to release" in capsys.readouterr().err

    def test_returns_two_for_an_unknown_version(self, changelog, capsys):
        assert main(["9.9.9", "--changelog", str(changelog)]) == 2
        assert "no section for" in capsys.readouterr().err

    def test_returns_two_when_the_file_is_missing(self, tmp_path, capsys):
        assert main(["1.0.0", "--changelog", str(tmp_path / "nope.md")]) == 2
        assert "error:" in capsys.readouterr().err
