# tests/test_release_check.py
"""Tests for the new-release check behind GET /status/version (issue #395)."""

from unittest.mock import MagicMock, patch

import pytest
import requests
from fastapi.testclient import TestClient

from api.config.swagger_settings import swagger_settings
from api.main import app
from api.services.auth_services import get_current_user
from api.services.status_services import release_check
from api.services.status_services.release_check import (
    changelog_url_for,
    get_version_info,
    parse_version,
)

RELEASE_PAGE = "https://github.com/national-data-platform/ep-api/releases/tag/v{v}"


def github_answer(tag, url=None):
    """A requests.Response stand-in for the GitHub latest-release API."""
    response = MagicMock()
    response.raise_for_status.return_value = None
    response.json.return_value = {
        "tag_name": tag,
        "html_url": url if url is not None else RELEASE_PAGE.format(v=tag.lstrip("v")),
    }
    return response


@pytest.fixture(autouse=True)
def fresh_cache(monkeypatch):
    """Each test starts with no cached release and a known installed version."""
    release_check.clear_cache()
    monkeypatch.setattr(swagger_settings, "swagger_version", "0.34.71")
    monkeypatch.setattr(swagger_settings, "release_check_enabled", True)
    yield
    release_check.clear_cache()


class TestParseVersion:
    def test_plain_and_v_prefixed(self):
        assert parse_version("0.34.71") == (0, 34, 71)
        assert parse_version("v1.0.0") == (1, 0, 0)

    def test_numeric_not_lexical_order(self):
        assert parse_version("0.34.100") > parse_version("0.34.71")

    @pytest.mark.parametrize("value", [None, "", "latest", "1.0", "1.0.0-rc1", 7])
    def test_unusable_values(self, value):
        assert parse_version(value) is None


class TestChangelogUrl:
    def test_github_release_page(self):
        assert changelog_url_for(RELEASE_PAGE.format(v="0.35.0")) == (
            "https://github.com/national-data-platform/ep-api/blob/v0.35.0/CHANGELOG.md"
        )

    def test_other_urls(self):
        assert changelog_url_for("https://example.org/releases/1") is None
        assert changelog_url_for("") is None
        assert changelog_url_for(None) is None


class TestGetVersionInfo:
    @patch("api.services.status_services.release_check.requests.get")
    def test_newer_release_available(self, mock_get):
        mock_get.return_value = github_answer("v0.35.0")

        info = get_version_info()

        assert info["current_version"] == "0.34.71"
        assert info["latest_version"] == "0.35.0"
        assert info["update_available"] is True
        assert info["release_url"] == RELEASE_PAGE.format(v="0.35.0")
        assert info["changelog_url"].endswith("/blob/v0.35.0/CHANGELOG.md")

    @patch("api.services.status_services.release_check.requests.get")
    def test_same_release(self, mock_get):
        mock_get.return_value = github_answer("v0.34.71")
        assert get_version_info()["update_available"] is False

    @patch("api.services.status_services.release_check.requests.get")
    def test_installed_is_newer(self, mock_get):
        mock_get.return_value = github_answer("v0.34.70")
        assert get_version_info()["update_available"] is False

    @patch("api.services.status_services.release_check.requests.get")
    def test_github_unreachable(self, mock_get):
        mock_get.side_effect = requests.ConnectionError("offline")

        info = get_version_info()

        assert info["current_version"] == "0.34.71"
        assert info["latest_version"] is None
        assert info["update_available"] is None

    @patch("api.services.status_services.release_check.requests.get")
    def test_http_error(self, mock_get):
        response = MagicMock()
        response.raise_for_status.side_effect = requests.HTTPError("403 rate limit")
        mock_get.return_value = response
        assert get_version_info()["update_available"] is None

    @patch("api.services.status_services.release_check.requests.get")
    def test_answer_without_a_version(self, mock_get):
        mock_get.return_value = github_answer("nightly", url="")
        info = get_version_info()
        assert info["latest_version"] is None
        assert info["update_available"] is None

    @patch("api.services.status_services.release_check.requests.get")
    def test_disabled_never_asks(self, mock_get, monkeypatch):
        monkeypatch.setattr(swagger_settings, "release_check_enabled", False)

        info = get_version_info()

        mock_get.assert_not_called()
        assert info["check_enabled"] is False
        assert info["update_available"] is None

    @patch("api.services.status_services.release_check.requests.get")
    def test_unparseable_installed_version(self, mock_get, monkeypatch):
        monkeypatch.setattr(swagger_settings, "swagger_version", "dev")
        mock_get.return_value = github_answer("v0.35.0")
        info = get_version_info()
        assert info["latest_version"] == "0.35.0"
        assert info["update_available"] is None

    @patch("api.services.status_services.release_check.requests.get")
    def test_release_is_cached(self, mock_get):
        mock_get.return_value = github_answer("v0.35.0")
        get_version_info()
        get_version_info()
        assert mock_get.call_count == 1

    @patch("api.services.status_services.release_check.requests.get")
    def test_failure_is_cached_too(self, mock_get):
        mock_get.side_effect = requests.Timeout("slow")
        get_version_info()
        get_version_info()
        assert mock_get.call_count == 1

    @patch("api.services.status_services.release_check.time.monotonic")
    @patch("api.services.status_services.release_check.requests.get")
    def test_cache_expires(self, mock_get, mock_now, monkeypatch):
        monkeypatch.setattr(swagger_settings, "release_check_interval_seconds", 60)
        mock_get.return_value = github_answer("v0.35.0")
        mock_now.return_value = 1000.0
        get_version_info()
        mock_now.return_value = 1061.0
        get_version_info()
        assert mock_get.call_count == 2


class TestVersionRoute:
    def test_requires_authentication(self):
        client = TestClient(app)
        assert client.get("/status/version").status_code in (401, 403)

    @patch("api.services.status_services.release_check.requests.get")
    def test_returns_version_info(self, mock_get):
        mock_get.return_value = github_answer("v0.35.0")
        app.dependency_overrides[get_current_user] = lambda: {"username": "u"}
        try:
            response = TestClient(app).get("/status/version")
        finally:
            app.dependency_overrides.pop(get_current_user, None)

        assert response.status_code == 200
        body = response.json()
        assert body["current_version"] == "0.34.71"
        assert body["latest_version"] == "0.35.0"
        assert body["update_available"] is True
