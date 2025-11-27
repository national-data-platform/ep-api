# tests/test_pelican_services.py
"""
Tests for Pelican service layer modules.

Tests for browse_federation, download_file, and import_metadata services.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from api.services.pelican_services.browse_federation import (
    browse_namespace,
    get_file_info
)
from api.services.pelican_services.download_file import (
    download_file,
    stream_file
)
from api.services.pelican_services.import_metadata import (
    import_file_as_resource
)


class TestBrowseNamespace:
    """Tests for browse_namespace function."""

    def test_browse_namespace_without_detail(self):
        """Test browsing namespace without details."""
        mock_repo = Mock()
        mock_repo.list_files.return_value = [
            {"name": "file1.nc"},
            {"name": "file2.nc"}
        ]

        result = browse_namespace(
            pelican_repo=mock_repo,
            path="/ospool/data",
            detail=False
        )

        assert result["success"] is True
        assert result["files"] == [{"name": "file1.nc"}, {"name": "file2.nc"}]
        assert result["count"] == 2
        mock_repo.list_files.assert_called_once_with("/ospool/data", detail=False)

    def test_browse_namespace_with_detail(self):
        """Test browsing namespace with details."""
        mock_repo = Mock()
        mock_repo.list_files.return_value = [
            {"name": "file1.nc", "size": 1024, "type": "file"}
        ]

        result = browse_namespace(
            pelican_repo=mock_repo,
            path="/ospool/data",
            detail=True
        )

        assert result["success"] is True
        assert len(result["files"]) == 1
        assert result["files"][0]["size"] == 1024
        mock_repo.list_files.assert_called_once_with("/ospool/data", detail=True)

    def test_browse_namespace_error_handling(self):
        """Test error handling when browsing fails."""
        mock_repo = Mock()
        mock_repo.list_files.side_effect = Exception("Connection failed")

        result = browse_namespace(
            pelican_repo=mock_repo,
            path="/ospool",
            detail=False
        )

        assert result["success"] is False
        assert "error" in result
        assert result["count"] == 0
        assert result["files"] == []


class TestGetFileInfo:
    """Tests for get_file_info function."""

    def test_get_file_info_success(self):
        """Test getting file info successfully."""
        mock_repo = Mock()
        mock_repo.file_info.return_value = {
            "name": "/ospool/data/test.nc",
            "size": 2048,
            "type": "file",
            "modified": 1234567890
        }

        result = get_file_info(
            pelican_repo=mock_repo,
            path="/ospool/data/test.nc"
        )

        assert result["success"] is True
        assert result["file"]["name"] == "/ospool/data/test.nc"
        assert result["file"]["size"] == 2048
        mock_repo.file_info.assert_called_once_with("/ospool/data/test.nc")

    def test_get_file_info_error(self):
        """Test error handling in get_file_info."""
        mock_repo = Mock()
        mock_repo.file_info.side_effect = FileNotFoundError("File not found")

        result = get_file_info(
            pelican_repo=mock_repo,
            path="/ospool/missing.nc"
        )

        assert result["success"] is False
        assert "error" in result


class TestDownloadFile:
    """Tests for download_file function."""

    def test_download_file_success(self):
        """Test successful file download."""
        mock_repo = Mock()
        mock_repo.read_file.return_value = b"netcdf data content"

        content = download_file(
            pelican_repo=mock_repo,
            path="/ospool/data/test.nc"
        )

        assert content == b"netcdf data content"
        mock_repo.read_file.assert_called_once_with("/ospool/data/test.nc")

    def test_download_file_error(self):
        """Test download error handling."""
        mock_repo = Mock()
        mock_repo.read_file.side_effect = Exception("Download failed")

        with pytest.raises(Exception, match="Download failed"):
            download_file(
                pelican_repo=mock_repo,
                path="/ospool/file.nc"
            )


class TestStreamFile:
    """Tests for stream_file function."""

    def test_stream_file_success(self):
        """Test opening file stream."""
        mock_repo = Mock()
        mock_stream = Mock()
        mock_repo.open_file.return_value = mock_stream

        stream = stream_file(
            pelican_repo=mock_repo,
            path="/ospool/data/large.nc"
        )

        assert stream == mock_stream
        mock_repo.open_file.assert_called_once_with("/ospool/data/large.nc", mode="rb")

    def test_stream_file_error(self):
        """Test stream error handling."""
        mock_repo = Mock()
        mock_repo.open_file.side_effect = Exception("Cannot open stream")

        with pytest.raises(Exception, match="Cannot open stream"):
            stream_file(
                pelican_repo=mock_repo,
                path="/ospool/data/file.nc"
            )


class TestImportFileAsResource:
    """Tests for import_file_as_resource function."""

    @patch("api.services.pelican_services.import_metadata.catalog_settings")
    def test_import_file_as_resource_success(self, mock_catalog):
        """Test successfully importing Pelican file as resource."""
        mock_repo = Mock()
        mock_repo.file_info.return_value = {
            "name": "/ospool/data/file.nc",
            "size": 1024,
            "type": "file"
        }

        mock_catalog.local_catalog.resource_create.return_value = {
            "id": "resource-456",
            "name": "Test Resource"
        }

        result = import_file_as_resource(
            pelican_repo=mock_repo,
            pelican_url="pelican://osg-htc.org/ospool/data/file.nc",
            package_id="package-123",
            resource_name="Test Resource",
            resource_description="Test description"
        )

        assert result["success"] is True
        assert result["resource"]["id"] == "resource-456"
        mock_catalog.local_catalog.resource_create.assert_called_once()

    @patch("api.services.pelican_services.import_metadata.catalog_settings")
    def test_import_without_description(self, mock_catalog):
        """Test importing without description."""
        mock_repo = Mock()
        mock_repo.file_info.return_value = {
            "name": "/file.nc",
            "size": 512,
            "type": "file"
        }

        mock_catalog.local_catalog.resource_create.return_value = {
            "id": "resource-789"
        }

        result = import_file_as_resource(
            pelican_repo=mock_repo,
            pelican_url="pelican://osg-htc.org/file.nc",
            package_id="package-123",
            resource_name="Resource"
        )

        assert result["success"] is True
        # Verify it was called with auto-generated description
        call_args = mock_catalog.local_catalog.resource_create.call_args[1]
        assert "Pelican federated file" in call_args["description"]

    def test_import_validates_url_scheme(self):
        """Test that non-pelican URLs are rejected."""
        mock_repo = Mock()

        result = import_file_as_resource(
            pelican_repo=mock_repo,
            pelican_url="http://example.com/file.nc",
            package_id="package-123",
            resource_name="Resource"
        )

        assert result["success"] is False
        assert "must start with pelican://" in result["error"]

    @patch("api.services.pelican_services.import_metadata.catalog_settings")
    def test_import_file_info_error(self, mock_catalog):
        """Test handling when file info retrieval fails."""
        mock_repo = Mock()
        mock_repo.file_info.side_effect = Exception("File not found")

        result = import_file_as_resource(
            pelican_repo=mock_repo,
            pelican_url="pelican://osg-htc.org/missing.nc",
            package_id="package-123",
            resource_name="Resource"
        )

        assert result["success"] is False
        assert "error" in result
