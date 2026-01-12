# tests/test_extra_services.py
"""Extra tests for services to increase coverage."""

import pytest
from unittest.mock import MagicMock, patch


class TestSearchDatasource:
    """Tests for search_datasource service."""

    @patch("api.services.datasource_services.search_datasource.catalog_settings")
    def test_search_invalid_server(self, mock_settings):
        """Test search with invalid server."""
        import asyncio
        from api.services.datasource_services.search_datasource import search_datasource

        async def run():
            with pytest.raises(Exception, match="Invalid server"):
                await search_datasource(server="invalid")

        asyncio.run(run())

    @patch("api.services.datasource_services.search_datasource.catalog_settings")
    def test_search_global_server(self, mock_settings):
        """Test search with global server."""
        import asyncio
        from api.services.datasource_services.search_datasource import search_datasource

        mock_repo = MagicMock()
        mock_repo.package_search.return_value = {"results": []}
        mock_settings.global_catalog = mock_repo

        async def run():
            await search_datasource(server="global")
            mock_repo.package_search.assert_called()

        asyncio.run(run())

    @patch("api.services.datasource_services.search_datasource.catalog_settings")
    def test_search_pre_ckan_server(self, mock_settings):
        """Test search with pre_ckan server."""
        import asyncio
        from api.services.datasource_services.search_datasource import search_datasource

        mock_repo = MagicMock()
        mock_repo.package_search.return_value = {"results": []}
        mock_settings.pre_catalog = mock_repo

        async def run():
            await search_datasource(server="pre_ckan")
            mock_repo.package_search.assert_called()

        asyncio.run(run())


class TestTstampToQuery:
    """Tests for tstamp_to_query function."""

    def test_too_many_elements(self):
        """Test timestamp with too many elements."""
        from api.services.datasource_services.search_datasource import tstamp_to_query

        with pytest.raises(ValueError, match="too many"):
            tstamp_to_query("2023/01/01/extra")

    def test_range_query(self):
        """Test range query."""
        from api.services.datasource_services.search_datasource import tstamp_to_query

        fq, count_max, sort = tstamp_to_query("2023-01-01/2023-12-31")
        assert "timestamp:" in fq
        assert count_max is None

    def test_past_query(self):
        """Test past query with <."""
        from api.services.datasource_services.search_datasource import tstamp_to_query

        fq, count_max, sort = tstamp_to_query("<2023-01-01")
        assert count_max == 1
        assert "desc" in sort


class TestStreamMatchesKeywords:
    """Tests for stream_matches_keywords function."""

    def test_matches_all(self):
        """Test matching all keywords."""
        from api.services.datasource_services.search_datasource import (
            stream_matches_keywords,
        )
        from unittest.mock import Mock

        stream = Mock()
        stream.__dict__ = {"name": "test", "title": "Test Dataset"}

        result = stream_matches_keywords(stream, ["test", "dataset"])
        assert result is True

    def test_no_match(self):
        """Test not matching keywords."""
        from api.services.datasource_services.search_datasource import (
            stream_matches_keywords,
        )
        from unittest.mock import Mock

        stream = Mock()
        stream.__dict__ = {"name": "test", "title": "Test"}

        result = stream_matches_keywords(stream, ["missing"])
        assert result is False


class TestSearchDatasourceWithResults:
    """Tests for search with results."""

    @patch("api.services.datasource_services.search_datasource.catalog_settings")
    def test_with_filter_list(self, mock_settings):
        """Test search with filter_list."""
        import asyncio
        from api.services.datasource_services.search_datasource import search_datasource

        mock_repo = MagicMock()
        mock_repo.package_search.return_value = {"results": []}
        mock_settings.local_catalog = mock_repo

        async def run():
            await search_datasource(filter_list=["type:dataset"], server="local")
            call_args = mock_repo.package_search.call_args
            assert "type:dataset" in call_args[1]["q"]

        asyncio.run(run())

    @patch("api.services.datasource_services.search_datasource.catalog_settings")
    def test_with_dataset_params(self, mock_settings):
        """Test search with dataset parameters."""
        import asyncio
        from api.services.datasource_services.search_datasource import search_datasource

        mock_repo = MagicMock()
        mock_repo.package_search.return_value = {"results": []}
        mock_settings.local_catalog = mock_repo

        async def run():
            await search_datasource(
                dataset_name="test",
                dataset_title="Title",
                owner_org="org",
                dataset_description="desc",
                server="local",
            )

        asyncio.run(run())

    @patch("api.services.datasource_services.search_datasource.catalog_settings")
    def test_with_timestamp(self, mock_settings):
        """Test search with timestamp."""
        import asyncio
        from api.services.datasource_services.search_datasource import search_datasource

        mock_repo = MagicMock()
        mock_repo.package_search.return_value = {"results": []}
        mock_settings.local_catalog = mock_repo

        async def run():
            await search_datasource(timestamp="2023-01-01", server="local")

        asyncio.run(run())

    @patch("api.services.datasource_services.search_datasource.catalog_settings")
    def test_not_found(self, mock_settings):
        """Test search with NotFound exception."""
        import asyncio
        from ckanapi import NotFound
        from api.services.datasource_services.search_datasource import search_datasource

        mock_repo = MagicMock()
        mock_repo.package_search.side_effect = NotFound()
        mock_settings.local_catalog = mock_repo

        async def run():
            result = await search_datasource(server="local")
            assert result == []

        asyncio.run(run())

    @patch("api.services.datasource_services.search_datasource.catalog_settings")
    def test_generic_exception(self, mock_settings):
        """Test search with generic exception."""
        import asyncio
        from api.services.datasource_services.search_datasource import search_datasource

        mock_repo = MagicMock()
        mock_repo.package_search.side_effect = Exception("DB error")
        mock_settings.local_catalog = mock_repo

        async def run():
            with pytest.raises(Exception, match="Error searching"):
                await search_datasource(server="local")

        asyncio.run(run())
