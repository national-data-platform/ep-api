"""Tests for the Pelican inline read operation (issue #262)."""

import base64
from unittest.mock import MagicMock, patch

import pytest

from api.config.swagger_settings import swagger_settings
from api.services.pelican_services.read_file import read_object


def _repo_returning(payload, error=None):
    """Build a repository whose open_file yields ``payload`` or raises."""
    repo = MagicMock()
    if error is not None:
        repo.open_file.side_effect = error
        return repo
    handle = MagicMock()
    handle.read.return_value = payload
    repo.open_file.return_value.__enter__.return_value = handle
    repo.open_file.return_value.__exit__.return_value = False
    return repo


class TestReadObjectService:
    """Tests for read_object."""

    def test_text_is_returned_as_text(self):
        repo = _repo_returning(b"time,value\n1,2\n")

        result = read_object(repo, "/public/data.csv", 1024)

        assert result["success"] is True
        assert result["encoding"] == "utf-8"
        assert result["content"] == "time,value\n1,2\n"
        assert result["size"] == 15
        assert result["path"] == "/public/data.csv"

    def test_binary_is_base64_encoded_not_rejected(self):
        """Pelican namespaces hold binary payloads; they must still read."""
        payload = b"\x89PNG\r\n\x1a\n\xff\xfe"
        repo = _repo_returning(payload)

        result = read_object(repo, "/public/img.png", 1024)

        assert result["success"] is True
        assert result["encoding"] == "base64"
        assert base64.b64decode(result["content"]) == payload

    def test_oversized_object_is_refused(self):
        """An object past the cap is refused rather than returned."""
        repo = _repo_returning(b"x" * 11)

        result = read_object(repo, "/public/big.bin", 10)

        assert result["success"] is False
        assert result["reason"] == "too_large"
        assert "/pelican/download" in result["error"]

    def test_cap_is_enforced_while_reading(self):
        """
        The cap must bound the read itself, otherwise an arbitrarily large
        object is pulled into memory just to be rejected.
        """
        repo = _repo_returning(b"x" * 11)

        read_object(repo, "/public/big.bin", 10)

        handle = repo.open_file.return_value.__enter__.return_value
        handle.read.assert_called_once_with(11)

    def test_missing_object_reports_not_found(self):
        repo = _repo_returning(None, error=FileNotFoundError("no such object"))

        result = read_object(repo, "/public/gone.txt", 1024)

        assert result["success"] is False
        assert result["reason"] == "not_found"

    def test_federation_failure_names_the_exception_type(self):
        """The class name is carried so the cause is identifiable."""
        repo = _repo_returning(None, error=ConnectionError("origin unreachable"))

        result = read_object(repo, "/public/data.csv", 1024)

        assert result["success"] is False
        assert result["reason"] == "unavailable"
        assert "ConnectionError" in result["error"]

    def test_exactly_at_the_cap_is_allowed(self):
        """The limit is inclusive; only past it is refused."""
        repo = _repo_returning(b"x" * 10)

        result = read_object(repo, "/public/edge.txt", 10)

        assert result["success"] is True
        assert result["size"] == 10


class TestMaxReadBytes:
    """Tests for the PELICAN_MAX_READ_BYTES resolution."""

    def test_default_when_unset(self):
        from api.routes.pelican_routes import DEFAULT_MAX_READ_BYTES, _max_read_bytes

        with patch.dict("os.environ", {}, clear=False):
            import os

            os.environ.pop("PELICAN_MAX_READ_BYTES", None)
            assert _max_read_bytes() == DEFAULT_MAX_READ_BYTES

    def test_explicit_value_is_used(self):
        from api.routes.pelican_routes import _max_read_bytes

        with patch.dict("os.environ", {"PELICAN_MAX_READ_BYTES": "2048"}):
            assert _max_read_bytes() == 2048

    def test_garbage_falls_back_to_default(self):
        """Settings allow extra keys, so a typo has to be caught here."""
        from api.routes.pelican_routes import DEFAULT_MAX_READ_BYTES, _max_read_bytes

        with patch.dict("os.environ", {"PELICAN_MAX_READ_BYTES": "ten megabytes"}):
            assert _max_read_bytes() == DEFAULT_MAX_READ_BYTES

    def test_non_positive_falls_back_to_default(self):
        from api.routes.pelican_routes import DEFAULT_MAX_READ_BYTES, _max_read_bytes

        with patch.dict("os.environ", {"PELICAN_MAX_READ_BYTES": "0"}):
            assert _max_read_bytes() == DEFAULT_MAX_READ_BYTES


class TestReadRoute:
    """Tests for GET /pelican/read."""

    @pytest.fixture(autouse=True)
    def _group_based_access_off(self):
        """
        Pin group-based access off rather than inherit it from ``.env``;
        the simulated users belong to no group (issue #268).
        """
        with patch.object(swagger_settings, "enable_group_based_access", False):
            yield

    @staticmethod
    def _client():
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from api.routes.pelican_routes import router

        app = FastAPI()
        app.include_router(router)
        return app, TestClient(app)

    @staticmethod
    def _as(roles):
        return lambda: {
            "roles": roles,
            "groups": [],
            "sub": "test_user",
            "username": "Test User",
        }

    def _get(self, app, client, roles=("ndp_viewer",)):
        from api.services.auth_services import get_current_user

        app.dependency_overrides[get_current_user] = self._as(list(roles))
        try:
            return client.get("/pelican/read", params={"path": "/public/data.csv"})
        finally:
            app.dependency_overrides.clear()

    @patch("api.routes.pelican_routes.get_pelican_repo")
    @patch("api.routes.pelican_routes.read_object")
    def test_success(self, mock_read, mock_get_repo):
        mock_get_repo.return_value = MagicMock()
        mock_read.return_value = {
            "success": True,
            "path": "/public/data.csv",
            "size": 4,
            "encoding": "utf-8",
            "content": "a,b\n",
        }
        app, client = self._client()

        response = self._get(app, client)

        assert response.status_code == 200
        assert response.json()["content"] == "a,b\n"

    @pytest.mark.parametrize(
        "reason,expected_status",
        [("not_found", 404), ("too_large", 413), ("unavailable", 502)],
    )
    @patch("api.routes.pelican_routes.get_pelican_repo")
    @patch("api.routes.pelican_routes.read_object")
    def test_failure_reasons_map_to_status_codes(
        self, mock_read, mock_get_repo, reason, expected_status
    ):
        mock_get_repo.return_value = MagicMock()
        mock_read.return_value = {
            "success": False,
            "path": "/public/data.csv",
            "error": "boom",
            "reason": reason,
        }
        app, client = self._client()

        response = self._get(app, client)

        assert response.status_code == expected_status
        assert response.json()["detail"] == "boom"

    @patch("api.routes.pelican_routes.read_object")
    def test_requires_authentication(self, mock_read):
        """The new route inherits the router gate added for issue #261."""
        _app, client = self._client()

        response = client.get("/pelican/read", params={"path": "/public/data.csv"})

        assert response.status_code == 401
        mock_read.assert_not_called()

    @patch("api.routes.pelican_routes.read_object")
    def test_rejects_user_without_role(self, mock_read):
        app, client = self._client()

        response = self._get(app, client, roles=())

        assert response.status_code == 403
        mock_read.assert_not_called()
