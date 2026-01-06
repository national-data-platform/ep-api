# tests/test_pelican_routes.py
"""Tests for Pelican routes."""

import pytest
from unittest.mock import MagicMock, patch
from fastapi import HTTPException


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
            "count": 1
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
        mock_get_file_info.return_value = {"success": True, "file": {"name": "test.txt"}}

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
            pelican_url="https://example.org/file.txt",
            package_id="pkg-123"
        )

        with pytest.raises(HTTPException) as exc_info:
            await import_metadata(request)

        assert exc_info.value.status_code == 400
