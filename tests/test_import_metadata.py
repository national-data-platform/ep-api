# tests/test_import_metadata.py
"""
Tests for Pelican import metadata service.
"""

import pytest
from unittest.mock import MagicMock, patch

from api.services.pelican_services.import_metadata import import_file_as_resource


class TestImportFileAsResource:
    """Test cases for import_file_as_resource function."""

    @patch("api.services.pelican_services.import_metadata.catalog_settings")
    def test_import_file_success(self, mock_catalog_settings):
        """Test successful file import."""
        mock_pelican_repo = MagicMock()
        mock_pelican_repo.file_info.return_value = {"size": 1024}

        mock_repository = MagicMock()
        mock_repository.resource_create.return_value = {
            "id": "res-123",
            "name": "test.txt",
            "url": "pelican://fed/path/test.txt",
        }
        mock_catalog_settings.local_catalog = mock_repository

        result = import_file_as_resource(
            pelican_repo=mock_pelican_repo,
            pelican_url="pelican://federation/path/test.txt",
            package_id="pkg-123",
        )

        assert result["success"] is True
        assert result["resource"]["id"] == "res-123"
        mock_pelican_repo.file_info.assert_called_once_with("/path/test.txt")

    @patch("api.services.pelican_services.import_metadata.catalog_settings")
    def test_import_file_with_custom_name(self, mock_catalog_settings):
        """Test file import with custom resource name."""
        mock_pelican_repo = MagicMock()
        mock_pelican_repo.file_info.return_value = {"size": 2048}

        mock_repository = MagicMock()
        mock_repository.resource_create.return_value = {
            "id": "res-456",
            "name": "custom_name.txt",
        }
        mock_catalog_settings.local_catalog = mock_repository

        result = import_file_as_resource(
            pelican_repo=mock_pelican_repo,
            pelican_url="pelican://fed/data/file.txt",
            package_id="pkg-456",
            resource_name="custom_name.txt",
        )

        assert result["success"] is True
        call_args = mock_repository.resource_create.call_args[1]
        assert call_args["name"] == "custom_name.txt"

    @patch("api.services.pelican_services.import_metadata.catalog_settings")
    def test_import_file_with_custom_description(self, mock_catalog_settings):
        """Test file import with custom description."""
        mock_pelican_repo = MagicMock()
        mock_pelican_repo.file_info.return_value = {"size": 512}

        mock_repository = MagicMock()
        mock_repository.resource_create.return_value = {"id": "res-789"}
        mock_catalog_settings.local_catalog = mock_repository

        result = import_file_as_resource(
            pelican_repo=mock_pelican_repo,
            pelican_url="pelican://fed/docs/readme.md",
            package_id="pkg-789",
            resource_description="Custom description",
        )

        assert result["success"] is True
        call_args = mock_repository.resource_create.call_args[1]
        assert call_args["description"] == "Custom description"

    @patch("api.services.pelican_services.import_metadata.catalog_settings")
    def test_import_file_default_resource_name(self, mock_catalog_settings):
        """Test that resource name defaults to filename."""
        mock_pelican_repo = MagicMock()
        mock_pelican_repo.file_info.return_value = {"size": 256}

        mock_repository = MagicMock()
        mock_repository.resource_create.return_value = {"id": "res-111"}
        mock_catalog_settings.local_catalog = mock_repository

        result = import_file_as_resource(
            pelican_repo=mock_pelican_repo,
            pelican_url="pelican://fed/path/to/myfile.csv",
            package_id="pkg-111",
        )

        assert result["success"] is True
        call_args = mock_repository.resource_create.call_args[1]
        assert call_args["name"] == "myfile.csv"

    def test_import_file_invalid_url(self):
        """Test import with invalid URL (not pelican://)."""
        mock_pelican_repo = MagicMock()

        result = import_file_as_resource(
            pelican_repo=mock_pelican_repo,
            pelican_url="http://example.com/file.txt",
            package_id="pkg-999",
        )

        assert result["success"] is False
        assert "must start with pelican://" in result["error"]

    @patch("api.services.pelican_services.import_metadata.catalog_settings")
    def test_import_file_info_error(self, mock_catalog_settings):
        """Test import when file info retrieval fails."""
        mock_pelican_repo = MagicMock()
        mock_pelican_repo.file_info.side_effect = Exception("File not found")

        result = import_file_as_resource(
            pelican_repo=mock_pelican_repo,
            pelican_url="pelican://fed/missing.txt",
            package_id="pkg-404",
        )

        assert result["success"] is False
        assert "File not found" in result["error"]

    @patch("api.services.pelican_services.import_metadata.catalog_settings")
    def test_import_file_resource_create_error(self, mock_catalog_settings):
        """Test import when resource creation fails."""
        mock_pelican_repo = MagicMock()
        mock_pelican_repo.file_info.return_value = {"size": 1024}

        mock_repository = MagicMock()
        mock_repository.resource_create.side_effect = Exception("Creation failed")
        mock_catalog_settings.local_catalog = mock_repository

        result = import_file_as_resource(
            pelican_repo=mock_pelican_repo,
            pelican_url="pelican://fed/test.txt",
            package_id="pkg-error",
        )

        assert result["success"] is False
        assert "Creation failed" in result["error"]

    @patch("api.services.pelican_services.import_metadata.catalog_settings")
    def test_import_file_creates_resource_with_correct_format(
        self, mock_catalog_settings
    ):
        """Test that imported resource has format set to 'pelican'."""
        mock_pelican_repo = MagicMock()
        mock_pelican_repo.file_info.return_value = {"size": 4096}

        mock_repository = MagicMock()
        mock_repository.resource_create.return_value = {"id": "res-format"}
        mock_catalog_settings.local_catalog = mock_repository

        result = import_file_as_resource(
            pelican_repo=mock_pelican_repo,
            pelican_url="pelican://fed/data.json",
            package_id="pkg-format",
        )

        assert result["success"] is True
        call_args = mock_repository.resource_create.call_args[1]
        assert call_args["format"] == "pelican"
        assert call_args["url"] == "pelican://fed/data.json"
