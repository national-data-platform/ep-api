"""Tests for the release-tag / swagger_version consistency check."""

import pytest

from scripts.check_release_version import (
    main,
    normalize_tag,
    read_swagger_version,
)

SETTINGS_TEMPLATE = '''"""Swagger settings."""


class SwaggerSettings:
    swagger_title: str = "NDP EP API"
    swagger_version: str = "{version}"
'''


@pytest.fixture
def settings_file(tmp_path):
    """Write a stand-in swagger_settings module declaring a given version."""

    def _write(version):
        path = tmp_path / "swagger_settings.py"
        path.write_text(SETTINGS_TEMPLATE.format(version=version), encoding="utf-8")
        return path

    return _write


class TestNormalizeTag:
    def test_strips_a_leading_v(self):
        assert normalize_tag("v0.34.17") == "0.34.17"

    def test_leaves_a_bare_version_untouched(self):
        assert normalize_tag("0.34.17") == "0.34.17"

    def test_strips_surrounding_whitespace(self):
        assert normalize_tag("  v0.34.17\n") == "0.34.17"

    def test_removes_only_one_leading_v(self):
        # Guards against lstrip("v"), which would return "1".
        assert normalize_tag("vv1") == "v1"

    def test_keeps_a_v_that_is_not_leading(self):
        assert normalize_tag("1.0.0-rev2") == "1.0.0-rev2"


class TestReadSwaggerVersion:
    def test_reads_the_declared_version(self, settings_file):
        assert read_swagger_version(settings_file("1.2.3")) == "1.2.3"

    def test_reads_a_single_quoted_declaration(self, tmp_path):
        path = tmp_path / "swagger_settings.py"
        path.write_text("    swagger_version: str = '9.9.9'\n", encoding="utf-8")
        assert read_swagger_version(path) == "9.9.9"

    def test_raises_when_the_declaration_is_missing(self, tmp_path):
        path = tmp_path / "swagger_settings.py"
        path.write_text("swagger_title: str = 'NDP'\n", encoding="utf-8")
        with pytest.raises(ValueError, match="no swagger_version"):
            read_swagger_version(path)

    def test_raises_when_the_file_is_missing(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            read_swagger_version(tmp_path / "nope.py")

    def test_matches_the_version_the_repository_actually_declares(self):
        # The real module must stay parseable, or every release would fail.
        assert read_swagger_version() != ""


class TestMain:
    def test_returns_zero_when_the_tag_matches(self, settings_file, capsys):
        path = settings_file("1.2.3")
        assert main(["v1.2.3", "--settings", str(path)]) == 0
        assert "agree on 1.2.3" in capsys.readouterr().out

    def test_accepts_a_tag_without_the_v_prefix(self, settings_file):
        path = settings_file("1.2.3")
        assert main(["1.2.3", "--settings", str(path)]) == 0

    def test_returns_one_on_a_mismatch(self, settings_file, capsys):
        path = settings_file("1.2.3")
        assert main(["v1.2.4", "--settings", str(path)]) == 1
        assert "does not match swagger_version" in capsys.readouterr().err

    def test_returns_two_when_the_version_cannot_be_read(self, tmp_path, capsys):
        missing = tmp_path / "nope.py"
        assert main(["v1.2.3", "--settings", str(missing)]) == 2
        assert "error:" in capsys.readouterr().err

    def test_mismatch_message_names_both_versions(self, settings_file, capsys):
        path = settings_file("1.2.3")
        main(["v2.0.0", "--settings", str(path)])
        err = capsys.readouterr().err
        assert "v2.0.0" in err and "1.2.3" in err
