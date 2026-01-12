# tests/test_pelican_repository.py
"""
Tests for PelicanRepository class.

Tests for the Pelican federation repository layer that wraps pelicanfs.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from api.repositories.pelican_repository import PelicanRepository


class TestPelicanRepositoryInit:
    """Tests for PelicanRepository initialization."""

    def test_init_with_defaults(self):
        """Test initialization with default parameters."""
        repo = PelicanRepository(federation_url="pelican://osg-htc.org")

        assert repo.federation_url == "pelican://osg-htc.org"
        assert repo.direct_reads is False
        assert repo.preferred_caches == []
        assert repo._fs is None

    def test_init_with_direct_reads(self):
        """Test initialization with direct reads enabled."""
        repo = PelicanRepository(
            federation_url="pelican://path-cc.io", direct_reads=True
        )

        assert repo.direct_reads is True

    def test_init_with_preferred_caches(self):
        """Test initialization with preferred caches."""
        caches = ["cache1.example.com", "cache2.example.com"]
        repo = PelicanRepository(
            federation_url="pelican://osg-htc.org", preferred_caches=caches
        )

        assert repo.preferred_caches == caches


class TestPelicanRepositoryFilesystemProperty:
    """Tests for filesystem lazy loading property."""

    @patch("api.repositories.pelican_repository.PelicanFileSystem")
    def test_fs_property_lazy_loads(self, mock_fs_class):
        """Test that fs property lazy-loads the filesystem."""
        mock_fs_instance = Mock()
        mock_fs_class.return_value = mock_fs_instance

        repo = PelicanRepository(federation_url="pelican://osg-htc.org")

        # fs should be None initially
        assert repo._fs is None

        # Accessing fs should create the filesystem
        fs = repo.fs

        assert fs == mock_fs_instance
        mock_fs_class.assert_called_once_with(
            "pelican://osg-htc.org", direct_reads=False, preferred_caches=[]
        )

    @patch("api.repositories.pelican_repository.PelicanFileSystem")
    def test_fs_property_caches_instance(self, mock_fs_class):
        """Test that fs property caches the filesystem instance."""
        mock_fs_instance = Mock()
        mock_fs_class.return_value = mock_fs_instance

        repo = PelicanRepository(federation_url="pelican://osg-htc.org")

        # Access fs twice
        fs1 = repo.fs
        fs2 = repo.fs

        # Should be the same instance
        assert fs1 is fs2
        # Should only create once
        assert mock_fs_class.call_count == 1


class TestListFiles:
    """Tests for list_files method."""

    @patch("api.repositories.pelican_repository.PelicanFileSystem")
    def test_list_files_basic(self, mock_fs_class):
        """Test basic file listing."""
        mock_fs = Mock()
        mock_fs.ls.return_value = [
            {"name": "file1.nc", "type": "file"},
            {"name": "file2.nc", "type": "file"},
        ]
        mock_fs_class.return_value = mock_fs

        repo = PelicanRepository(federation_url="pelican://osg-htc.org")
        files = repo.list_files("/ospool/data")

        assert len(files) == 2
        mock_fs.ls.assert_called_once_with("/ospool/data", detail=False)

    @patch("api.repositories.pelican_repository.PelicanFileSystem")
    def test_list_files_with_detail(self, mock_fs_class):
        """Test file listing with details."""
        mock_fs = Mock()
        mock_fs.ls.return_value = [
            {"name": "file1.nc", "type": "file", "size": 1024},
            {"name": "dir1", "type": "directory"},
        ]
        mock_fs_class.return_value = mock_fs

        repo = PelicanRepository(federation_url="pelican://osg-htc.org")
        files = repo.list_files("/ospool", detail=True)

        assert len(files) == 2
        assert files[0]["size"] == 1024
        mock_fs.ls.assert_called_once_with("/ospool", detail=True)


class TestReadFile:
    """Tests for read_file method."""

    @patch("api.repositories.pelican_repository.PelicanFileSystem")
    def test_read_file_success(self, mock_fs_class):
        """Test successful file reading."""
        mock_fs = Mock()
        mock_fs.cat.return_value = b"netcdf data content"
        mock_fs_class.return_value = mock_fs

        repo = PelicanRepository(federation_url="pelican://osg-htc.org")
        content = repo.read_file("/ospool/data/test.nc")

        assert content == b"netcdf data content"
        mock_fs.cat.assert_called_once_with("/ospool/data/test.nc")


class TestFileInfo:
    """Tests for file_info method."""

    @patch("api.repositories.pelican_repository.PelicanFileSystem")
    def test_file_info_success(self, mock_fs_class):
        """Test getting file info."""
        mock_fs = Mock()
        mock_fs.info.return_value = {
            "name": "/ospool/data/test.nc",
            "type": "file",
            "size": 2048,
            "mtime": 1234567890,
        }
        mock_fs_class.return_value = mock_fs

        repo = PelicanRepository(federation_url="pelican://osg-htc.org")
        info = repo.file_info("/ospool/data/test.nc")

        assert info["name"] == "/ospool/data/test.nc"
        assert info["size"] == 2048
        mock_fs.info.assert_called_once_with("/ospool/data/test.nc")


class TestFileExists:
    """Tests for file_exists method."""

    @patch("api.repositories.pelican_repository.PelicanFileSystem")
    def test_file_exists_returns_true(self, mock_fs_class):
        """Test file_exists returns True when file exists."""
        mock_fs = Mock()
        mock_fs.exists.return_value = True
        mock_fs_class.return_value = mock_fs

        repo = PelicanRepository(federation_url="pelican://osg-htc.org")
        exists = repo.file_exists("/ospool/data/test.nc")

        assert exists is True
        mock_fs.exists.assert_called_once_with("/ospool/data/test.nc")

    @patch("api.repositories.pelican_repository.PelicanFileSystem")
    def test_file_exists_returns_false(self, mock_fs_class):
        """Test file_exists returns False when file doesn't exist."""
        mock_fs = Mock()
        mock_fs.exists.return_value = False
        mock_fs_class.return_value = mock_fs

        repo = PelicanRepository(federation_url="pelican://osg-htc.org")
        exists = repo.file_exists("/ospool/data/missing.nc")

        assert exists is False


class TestOpenFile:
    """Tests for open_file method."""

    @patch("api.repositories.pelican_repository.PelicanFileSystem")
    def test_open_file_read_mode(self, mock_fs_class):
        """Test opening file in read mode."""
        mock_fs = Mock()
        mock_file = MagicMock()
        mock_fs.open.return_value = mock_file
        mock_fs_class.return_value = mock_fs

        repo = PelicanRepository(federation_url="pelican://osg-htc.org")
        file_handle = repo.open_file("/ospool/data/test.nc", mode="rb")

        assert file_handle == mock_file
        mock_fs.open.assert_called_once_with("/ospool/data/test.nc", mode="rb")

    @patch("api.repositories.pelican_repository.PelicanFileSystem")
    def test_open_file_default_mode(self, mock_fs_class):
        """Test opening file with default mode."""
        mock_fs = Mock()
        mock_file = MagicMock()
        mock_fs.open.return_value = mock_file
        mock_fs_class.return_value = mock_fs

        repo = PelicanRepository(federation_url="pelican://osg-htc.org")
        file_handle = repo.open_file("/ospool/data/test.nc")

        mock_fs.open.assert_called_once_with("/ospool/data/test.nc", mode="rb")


class TestCheckHealth:
    """Tests for check_health method."""

    @patch("api.repositories.pelican_repository.PelicanFileSystem")
    def test_check_health_success(self, mock_fs_class):
        """Test successful health check."""
        mock_fs = Mock()
        mock_fs.ls.return_value = []
        mock_fs_class.return_value = mock_fs

        repo = PelicanRepository(federation_url="pelican://osg-htc.org")
        is_healthy = repo.check_health()

        assert is_healthy is True
        mock_fs.ls.assert_called_once_with("/")

    @patch("api.repositories.pelican_repository.PelicanFileSystem")
    def test_check_health_failure(self, mock_fs_class):
        """Test health check failure."""
        mock_fs = Mock()
        mock_fs.ls.side_effect = Exception("Connection failed")
        mock_fs_class.return_value = mock_fs

        repo = PelicanRepository(federation_url="pelican://osg-htc.org")
        is_healthy = repo.check_health()

        assert is_healthy is False


class TestRepositoryProperties:
    """Tests for repository properties and configuration."""

    @patch("api.repositories.pelican_repository.PelicanFileSystem")
    def test_repository_attributes(self, mock_fs_class):
        """Test repository stores configuration correctly."""
        repo = PelicanRepository(
            federation_url="pelican://osg-htc.org",
            direct_reads=True,
            preferred_caches=["cache1", "cache2"],
        )

        assert repo.federation_url == "pelican://osg-htc.org"
        assert repo.direct_reads is True
        assert repo.preferred_caches == ["cache1", "cache2"]


class TestErrorHandling:
    """Tests for error handling in various methods."""

    @patch("api.repositories.pelican_repository.PelicanFileSystem")
    def test_read_file_error_propagates(self, mock_fs_class):
        """Test that read errors propagate correctly."""
        mock_fs = Mock()
        mock_fs.cat.side_effect = FileNotFoundError("File not found")
        mock_fs_class.return_value = mock_fs

        repo = PelicanRepository(federation_url="pelican://osg-htc.org")

        with pytest.raises(FileNotFoundError):
            repo.read_file("/ospool/missing.nc")

    @patch("api.repositories.pelican_repository.PelicanFileSystem")
    def test_list_files_error_propagates(self, mock_fs_class):
        """Test that listing errors propagate correctly."""
        mock_fs = Mock()
        mock_fs.ls.side_effect = PermissionError("Access denied")
        mock_fs_class.return_value = mock_fs

        repo = PelicanRepository(federation_url="pelican://osg-htc.org")

        with pytest.raises(PermissionError):
            repo.list_files("/restricted")
