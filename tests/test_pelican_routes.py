# tests/test_pelican_routes.py
"""Tests for Pelican routes."""

import pytest
from unittest.mock import MagicMock, patch
from fastapi import HTTPException

from api.config.affinities_settings import affinities_settings
from api.config.swagger_settings import swagger_settings


class TestListFederations:
    """Tests for list_federations endpoint."""

    @pytest.mark.asyncio
    @patch("api.routes.pelican_routes.os.getenv")
    async def test_list_federations_no_custom(self, mock_getenv):
        """Test listing federations without custom URL."""
        from api.routes.pelican_routes import list_federations

        mock_getenv.return_value = None

        result = await list_federations()

        assert result["success"] is True
        assert "osdf" in result["federations"]
        assert result["count"] == 2

    @pytest.mark.asyncio
    @patch("api.routes.pelican_routes.os.getenv")
    async def test_list_federations_with_custom(self, mock_getenv):
        """Test listing federations with custom URL."""
        from api.routes.pelican_routes import list_federations

        mock_getenv.return_value = "pelican://custom.org"

        result = await list_federations()

        assert result["success"] is True
        assert "custom" in result["federations"]
        assert result["count"] == 3


class TestBrowseFiles:
    """Tests for browse_files endpoint."""

    @pytest.mark.asyncio
    @patch("api.routes.pelican_routes.get_pelican_repo")
    @patch("api.routes.pelican_routes.browse_namespace")
    async def test_browse_files_success(self, mock_browse, mock_get_repo):
        """Test successful file browsing."""
        from api.routes.pelican_routes import browse_files

        mock_repo = MagicMock()
        mock_get_repo.return_value = mock_repo
        mock_browse.return_value = {
            "success": True,
            "path": "/test/path",
            "files": [{"name": "file1.txt"}],
            "count": 1,
        }

        result = await browse_files(path="/test/path", federation="osdf", detail=False)

        assert result["success"] is True
        assert result["count"] == 1

    @pytest.mark.asyncio
    @patch("api.routes.pelican_routes.get_pelican_repo")
    @patch("api.routes.pelican_routes.browse_namespace")
    async def test_browse_files_not_found(self, mock_browse, mock_get_repo):
        """Test browsing non-existent path."""
        from api.routes.pelican_routes import browse_files

        mock_repo = MagicMock()
        mock_get_repo.return_value = mock_repo
        mock_browse.return_value = {"success": False, "error": "Path not found"}

        with pytest.raises(HTTPException) as exc_info:
            await browse_files(path="/nonexistent", federation="osdf", detail=False)

        assert exc_info.value.status_code == 404


class TestGetInfo:
    """Tests for get_info endpoint."""

    @pytest.mark.asyncio
    @patch("api.routes.pelican_routes.get_pelican_repo")
    @patch("api.routes.pelican_routes.get_file_info")
    async def test_get_info_success(self, mock_get_file_info, mock_get_repo):
        """Test successful file info retrieval."""
        from api.routes.pelican_routes import get_info

        mock_repo = MagicMock()
        mock_get_repo.return_value = mock_repo
        mock_get_file_info.return_value = {
            "success": True,
            "file": {"name": "test.txt"},
        }

        result = await get_info(path="/test/file.txt", federation="osdf")

        assert result["success"] is True

    @pytest.mark.asyncio
    @patch("api.routes.pelican_routes.get_pelican_repo")
    @patch("api.routes.pelican_routes.get_file_info")
    async def test_get_info_not_found(self, mock_get_file_info, mock_get_repo):
        """Test file info for non-existent file."""
        from api.routes.pelican_routes import get_info

        mock_repo = MagicMock()
        mock_get_repo.return_value = mock_repo
        mock_get_file_info.return_value = {"success": False, "error": "Not found"}

        with pytest.raises(HTTPException) as exc_info:
            await get_info(path="/nonexistent", federation="osdf")

        assert exc_info.value.status_code == 404


class TestDownload:
    """Tests for download endpoint."""

    @pytest.mark.asyncio
    @patch("api.routes.pelican_routes.get_pelican_repo")
    @patch("api.routes.pelican_routes.download_file")
    async def test_download_success(self, mock_download, mock_get_repo):
        """Test successful file download."""
        from api.routes.pelican_routes import download

        mock_repo = MagicMock()
        mock_get_repo.return_value = mock_repo
        mock_download.return_value = b"file contents"

        result = await download(path="/test/file.txt", federation="osdf", stream=False)

        assert result.body == b"file contents"


class TestImportMetadata:
    """Tests for import_metadata endpoint."""

    @pytest.mark.asyncio
    async def test_import_metadata_invalid_url(self):
        """Test import with invalid URL."""
        from api.routes.pelican_routes import import_metadata, ImportMetadataRequest

        request = ImportMetadataRequest(
            pelican_url="https://example.org/file.txt", package_id="pkg-123"
        )

        with pytest.raises(HTTPException) as exc_info:
            await import_metadata(request)

        assert exc_info.value.status_code == 400


class TestPelicanRoutesAuthorization:
    """
    The Pelican routes shipped without any authentication (issue #261), so
    these tests pin the gate down: no anonymous access, no access without a
    role, and the write route demands more than the read routes.
    """

    @pytest.fixture(autouse=True)
    def _group_based_access_off(self):
        """
        Pin group-based access off rather than inherit it from ``.env``.

        With it on, the dependencies check group membership before roles,
        and the simulated users belong to no group — so these tests failed
        on any machine that enabled it, while passing in CI (issue #268).
        The group branch is covered explicitly further down instead.
        """
        with patch.object(swagger_settings, "enable_group_based_access", False):
            yield

    @staticmethod
    def _client():
        """Mount the Pelican router on a bare app, independent of
        ``PELICAN_ENABLED`` and of the rest of the application."""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from api.routes.pelican_routes import router

        app = FastAPI()
        app.include_router(router)
        return app, TestClient(app)

    @staticmethod
    def _as(roles):
        """Build a ``get_current_user`` override for a user with ``roles``."""
        return lambda: {
            "roles": roles,
            "groups": [],
            "sub": "test_user",
            "username": "Test User",
        }

    def test_read_route_rejects_anonymous_caller(self):
        """A request with no Authorization header never reaches the route."""
        _app, client = self._client()

        response = client.get("/pelican/federations")

        assert response.status_code == 401

    @patch("api.routes.pelican_routes.browse_namespace")
    def test_browse_rejects_anonymous_caller(self, mock_browse):
        """Browsing is refused before the federation is contacted."""
        _app, client = self._client()

        response = client.get("/pelican/browse", params={"path": "/public"})

        assert response.status_code == 401
        mock_browse.assert_not_called()

    @patch("api.routes.pelican_routes.download_file")
    def test_download_rejects_anonymous_caller(self, mock_download):
        """Downloading is refused before any byte leaves the federation."""
        _app, client = self._client()

        response = client.get("/pelican/download", params={"path": "/public/f.txt"})

        assert response.status_code == 401
        mock_download.assert_not_called()

    def test_read_route_rejects_user_without_role(self):
        """An authenticated user with no role tier still gets 403."""
        from api.services.auth_services import get_current_user

        app, client = self._client()
        app.dependency_overrides[get_current_user] = self._as([])
        try:
            response = client.get("/pelican/federations")
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 403

    def test_read_route_allows_viewer(self):
        """A viewer may read: the gate is authorization, not a blanket block."""
        from api.services.auth_services import get_current_user

        app, client = self._client()
        app.dependency_overrides[get_current_user] = self._as(["ndp_viewer"])
        try:
            response = client.get("/pelican/federations")
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 200
        assert response.json()["success"] is True

    @patch("api.routes.pelican_routes.import_file_as_resource")
    def test_import_metadata_rejects_viewer(self, mock_import):
        """The write route is stricter than the read gate it sits behind."""
        from api.services.auth_services import get_current_user

        app, client = self._client()
        app.dependency_overrides[get_current_user] = self._as(["ndp_viewer"])
        try:
            response = client.post(
                "/pelican/import-metadata",
                json={
                    "pelican_url": "pelican://osg-htc.org/public/f.txt",
                    "package_id": "pkg-1",
                },
            )
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 403
        mock_import.assert_not_called()

    @patch("api.routes.pelican_routes.get_pelican_repo")
    @patch("api.routes.pelican_routes.import_file_as_resource")
    def test_import_metadata_allows_writer(self, mock_import, mock_get_repo):
        """A writer reaches the route body."""
        from api.services.auth_services import get_current_user

        mock_get_repo.return_value = MagicMock()
        mock_import.return_value = {"success": True, "id": "res-1"}

        app, client = self._client()
        app.dependency_overrides[get_current_user] = self._as(["ndp_editor"])
        try:
            response = client.post(
                "/pelican/import-metadata",
                json={
                    "pelican_url": "pelican://osg-htc.org/public/f.txt",
                    "package_id": "pkg-1",
                },
            )
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 200
        mock_import.assert_called_once()

    @pytest.mark.parametrize(
        "groups,expected_status",
        [([], 403), (["/pelican-readers"], 200)],
    )
    def test_group_based_access_gates_the_read_routes(self, groups, expected_status):
        """
        With group-based access on, a viewer outside the configured groups
        is refused and one inside is let through. Covered on purpose here,
        since the other tests pin the feature off.
        """
        from api.services.auth_services import get_current_user

        app, client = self._client()
        app.dependency_overrides[get_current_user] = lambda: {
            "roles": ["ndp_viewer"],
            "groups": groups,
            "sub": "test_user",
            "username": "Test User",
        }
        try:
            with (
                patch.object(swagger_settings, "enable_group_based_access", True),
                patch.object(swagger_settings, "group_names", "pelican-readers"),
                patch.object(affinities_settings, "ep_uuid", ""),
            ):
                response = client.get("/pelican/federations")
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == expected_status
