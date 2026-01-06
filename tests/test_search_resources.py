# tests/test_search_resources.py
"""Tests for search_resources service."""

import pytest
from unittest.mock import MagicMock, patch

from api.services.dataset_services.search_resources import search_resources


class TestSearchResources:
    """Tests for search_resources service."""

    def test_search_resources_success(self):
        """Test successful resource search."""
        mock_repo = MagicMock()
        mock_repo.resource_search.return_value = {
            "count": 2,
            "results": [
                {"id": "res-1", "name": "Resource 1"},
                {"id": "res-2", "name": "Resource 2"},
            ],
        }

        result = search_resources(query="test", repository=mock_repo)

        assert result["count"] == 2
        assert len(result["results"]) == 2
        mock_repo.resource_search.assert_called_once()

    def test_search_resources_with_all_filters(self):
        """Test resource search with all filter parameters."""
        mock_repo = MagicMock()
        mock_repo.resource_search.return_value = {"count": 1, "results": []}

        search_resources(
            query="test",
            name="my-resource",
            url="http://example.com",
            format="CSV",
            description="test data",
            limit=50,
            offset=10,
            repository=mock_repo,
        )

        mock_repo.resource_search.assert_called_once_with(
            query="test",
            name="my-resource",
            url="http://example.com",
            format="CSV",
            description="test data",
            limit=50,
            offset=10,
        )

    def test_search_resources_error(self):
        """Test resource search error handling."""
        mock_repo = MagicMock()
        mock_repo.resource_search.side_effect = Exception("Database error")

        with pytest.raises(Exception) as exc_info:
            search_resources(query="test", repository=mock_repo)

        assert "Error searching resources" in str(exc_info.value)

    @patch("api.services.dataset_services.search_resources.catalog_settings")
    def test_search_resources_uses_default_catalog(self, mock_catalog_settings):
        """Test that default catalog is used when no repository provided."""
        mock_repo = MagicMock()
        mock_repo.resource_search.return_value = {"count": 0, "results": []}
        mock_catalog_settings.local_catalog = mock_repo

        result = search_resources(query="test")

        assert result["count"] == 0
        mock_repo.resource_search.assert_called_once()

    def test_search_resources_empty_results(self):
        """Test resource search with no results."""
        mock_repo = MagicMock()
        mock_repo.resource_search.return_value = {"count": 0, "results": []}

        result = search_resources(query="nonexistent", repository=mock_repo)

        assert result["count"] == 0
        assert result["results"] == []

    def test_search_resources_default_pagination(self):
        """Test default pagination values."""
        mock_repo = MagicMock()
        mock_repo.resource_search.return_value = {"count": 0, "results": []}

        search_resources(repository=mock_repo)

        mock_repo.resource_search.assert_called_once_with(
            query=None,
            name=None,
            url=None,
            format=None,
            description=None,
            limit=100,
            offset=0,
        )

    def test_search_resources_by_name_only(self):
        """Test resource search by name only."""
        mock_repo = MagicMock()
        mock_repo.resource_search.return_value = {
            "count": 1,
            "results": [{"id": "res-1", "name": "matching-name"}],
        }

        result = search_resources(name="matching", repository=mock_repo)

        assert result["count"] == 1
        mock_repo.resource_search.assert_called_once_with(
            query=None,
            name="matching",
            url=None,
            format=None,
            description=None,
            limit=100,
            offset=0,
        )

    def test_search_resources_by_format_only(self):
        """Test resource search by format only."""
        mock_repo = MagicMock()
        mock_repo.resource_search.return_value = {
            "count": 5,
            "results": [{"id": f"res-{i}", "format": "CSV"} for i in range(5)],
        }

        result = search_resources(format="CSV", repository=mock_repo)

        assert result["count"] == 5

    def test_search_resources_by_url_only(self):
        """Test resource search by URL only."""
        mock_repo = MagicMock()
        mock_repo.resource_search.return_value = {"count": 1, "results": []}

        search_resources(url="example.com", repository=mock_repo)

        mock_repo.resource_search.assert_called_once_with(
            query=None,
            name=None,
            url="example.com",
            format=None,
            description=None,
            limit=100,
            offset=0,
        )
