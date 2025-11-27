# tests/test_download_helper.py
"""
Tests for download_helper service module.

This module tests the unified download interface that automatically
detects and handles different URL schemes (HTTP, Pelican, S3).
"""

import pytest
import os
from unittest.mock import Mock, patch, AsyncMock
import httpx

from api.services.download_helper import (
    is_pelican_url,
    get_pelican_repo_for_url,
    download_resource,
    download_from_pelican,
    download_from_http,
    stream_resource,
    stream_from_pelican
)


class TestIsPelicanUrl:
    """Tests for is_pelican_url function."""

    def test_pelican_url_returns_true(self):
        """Test that pelican:// URLs are correctly identified."""
        assert is_pelican_url("pelican://osg-htc.org/path/to/file") is True

    def test_http_url_returns_false(self):
        """Test that HTTP URLs return False."""
        assert is_pelican_url("http://example.com/file") is False

    def test_https_url_returns_false(self):
        """Test that HTTPS URLs return False."""
        assert is_pelican_url("https://example.com/file") is False

    def test_s3_url_returns_false(self):
        """Test that S3 URLs return False."""
        assert is_pelican_url("s3://bucket/key") is False

    def test_empty_string_returns_false(self):
        """Test that empty string returns False."""
        assert is_pelican_url("") is False


class TestGetPelicanRepoForUrl:
    """Tests for get_pelican_repo_for_url function."""

    @patch.dict(os.environ, {"PELICAN_DIRECT_READS": "false"})
    def test_extracts_federation_from_url(self):
        """Test federation extraction from pelican URL."""
        url = "pelican://osg-htc.org/ospool/data/file.nc"

        with patch("api.services.download_helper.PelicanRepository") as mock_repo:
            get_pelican_repo_for_url(url)

            mock_repo.assert_called_once_with(
                federation_url="pelican://osg-htc.org",
                direct_reads=False
            )

    @patch.dict(os.environ, {"PELICAN_DIRECT_READS": "true"})
    def test_respects_direct_reads_env_var(self):
        """Test that PELICAN_DIRECT_READS environment variable is respected."""
        url = "pelican://path-cc.io/data/file"

        with patch("api.services.download_helper.PelicanRepository") as mock_repo:
            get_pelican_repo_for_url(url)

            mock_repo.assert_called_once_with(
                federation_url="pelican://path-cc.io",
                direct_reads=True
            )

    def test_raises_error_for_non_pelican_url(self):
        """Test that ValueError is raised for non-pelican URLs."""
        with pytest.raises(ValueError, match="must start with pelican://"):
            get_pelican_repo_for_url("http://example.com/file")


class TestDownloadFromHttp:
    """Tests for download_from_http function."""

    @pytest.mark.asyncio
    async def test_successful_http_download(self):
        """Test successful HTTP download."""
        url = "http://example.com/file.txt"
        expected_content = b"test content"

        mock_response = Mock()
        mock_response.content = expected_content
        mock_response.raise_for_status = Mock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)

            content, error = await download_from_http(url)

            assert content == expected_content
            assert error is None

    @pytest.mark.asyncio
    async def test_http_404_error(self):
        """Test handling of HTTP 404 error."""
        url = "http://example.com/notfound.txt"

        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.reason_phrase = "Not Found"

        http_error = httpx.HTTPStatusError(
            "404 Not Found",
            request=Mock(),
            response=mock_response
        )

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(side_effect=http_error)

            content, error = await download_from_http(url)

            assert content is None
            assert "404" in error
            assert "Not Found" in error

    @pytest.mark.asyncio
    async def test_http_network_error(self):
        """Test handling of network errors."""
        url = "http://example.com/file.txt"

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                side_effect=httpx.ConnectError("Connection failed")
            )

            content, error = await download_from_http(url)

            assert content is None
            assert "HTTP download error" in error


class TestDownloadFromPelican:
    """Tests for download_from_pelican function."""

    @pytest.mark.asyncio
    async def test_successful_pelican_download(self):
        """Test successful download from Pelican."""
        url = "pelican://osg-htc.org/ospool/data/test.nc"
        expected_content = b"netcdf data"

        mock_repo = Mock()
        mock_repo.read_file = Mock(return_value=expected_content)

        with patch("api.services.download_helper.get_pelican_repo_for_url", return_value=mock_repo):
            content, error = await download_from_pelican(url)

            assert content == expected_content
            assert error is None
            mock_repo.read_file.assert_called_once_with("/ospool/data/test.nc")

    @pytest.mark.asyncio
    async def test_pelican_download_error(self):
        """Test error handling in Pelican download."""
        url = "pelican://osg-htc.org/ospool/invalid/file"

        mock_repo = Mock()
        mock_repo.read_file = Mock(side_effect=Exception("File not found"))

        with patch("api.services.download_helper.get_pelican_repo_for_url", return_value=mock_repo):
            content, error = await download_from_pelican(url)

            assert content is None
            assert "Pelican download error" in error
            assert "File not found" in error


class TestDownloadResource:
    """Tests for download_resource unified function."""

    @pytest.mark.asyncio
    async def test_routes_pelican_url(self):
        """Test that pelican:// URLs are routed correctly."""
        url = "pelican://osg-htc.org/data/file"

        with patch("api.services.download_helper.download_from_pelican", new_callable=AsyncMock) as mock_download:
            mock_download.return_value = (b"data", None)

            await download_resource(url)

            mock_download.assert_called_once_with(url)

    @pytest.mark.asyncio
    async def test_routes_http_url(self):
        """Test that http:// URLs are routed correctly."""
        url = "http://example.com/file"

        with patch("api.services.download_helper.download_from_http", new_callable=AsyncMock) as mock_download:
            mock_download.return_value = (b"data", None)

            await download_resource(url)

            mock_download.assert_called_once_with(url)

    @pytest.mark.asyncio
    async def test_routes_https_url(self):
        """Test that https:// URLs are routed correctly."""
        url = "https://example.com/file"

        with patch("api.services.download_helper.download_from_http", new_callable=AsyncMock) as mock_download:
            mock_download.return_value = (b"data", None)

            await download_resource(url)

            mock_download.assert_called_once_with(url)

    @pytest.mark.asyncio
    async def test_s3_url_not_implemented(self):
        """Test that S3 URLs return not implemented error."""
        url = "s3://bucket/key"

        content, error = await download_resource(url)

        assert content is None
        assert "S3 downloads not yet implemented" in error

    @pytest.mark.asyncio
    async def test_unsupported_url_scheme(self):
        """Test that unsupported URL schemes are rejected."""
        url = "ftp://example.com/file"

        content, error = await download_resource(url)

        assert content is None
        assert "Unsupported URL scheme" in error

    @pytest.mark.asyncio
    async def test_exception_handling(self):
        """Test that exceptions are caught and returned as errors."""
        url = "pelican://test/file"

        with patch("api.services.download_helper.download_from_pelican", new_callable=AsyncMock) as mock_download:
            mock_download.side_effect = RuntimeError("Unexpected error")

            content, error = await download_resource(url)

            assert content is None
            assert "Unexpected error" in error


class TestStreamResource:
    """Tests for stream_resource function."""

    def test_streams_pelican_url(self):
        """Test streaming from Pelican URL."""
        url = "pelican://osg-htc.org/data/file"
        mock_stream = Mock()

        with patch("api.services.download_helper.stream_from_pelican", return_value=mock_stream):
            result = stream_resource(url)

            assert result == mock_stream

    def test_raises_error_for_http_url(self):
        """Test that HTTP URLs raise error (not supported for streaming)."""
        url = "http://example.com/file"

        with pytest.raises(ValueError, match="Streaming not yet supported"):
            stream_resource(url)

    def test_raises_error_for_s3_url(self):
        """Test that S3 URLs raise error (not supported for streaming)."""
        url = "s3://bucket/key"

        with pytest.raises(ValueError, match="Streaming not yet supported"):
            stream_resource(url)


class TestStreamFromPelican:
    """Tests for stream_from_pelican function."""

    def test_opens_pelican_file_stream(self):
        """Test opening Pelican file for streaming."""
        url = "pelican://osg-htc.org/ospool/data/large.nc"
        mock_stream = Mock()

        mock_repo = Mock()
        mock_repo.open_file = Mock(return_value=mock_stream)

        with patch("api.services.download_helper.get_pelican_repo_for_url", return_value=mock_repo):
            result = stream_from_pelican(url)

            assert result == mock_stream
            mock_repo.open_file.assert_called_once_with("/ospool/data/large.nc", mode="rb")

    def test_extracts_correct_path(self):
        """Test that file path is correctly extracted from URL."""
        url = "pelican://path-cc.io/deep/nested/path/file.dat"

        mock_repo = Mock()
        mock_repo.open_file = Mock(return_value=Mock())

        with patch("api.services.download_helper.get_pelican_repo_for_url", return_value=mock_repo):
            stream_from_pelican(url)

            mock_repo.open_file.assert_called_once_with("/deep/nested/path/file.dat", mode="rb")
