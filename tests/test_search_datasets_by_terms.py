# tests/test_search_datasets_by_terms.py
"""Tests for search_datasets_by_terms service."""

import pytest
from unittest.mock import MagicMock, patch
from fastapi import HTTPException
from ckanapi import CKANAPIError, NotFound
import requests.exceptions

from api.services.datasource_services.search_datasets_by_terms import (
    search_datasets_by_terms,
    escape_solr_special_chars,
)


class TestEscapeSolrSpecialChars:
    """Tests for escape_solr_special_chars function."""

    def test_escape_plus(self):
        assert escape_solr_special_chars("test+query") == "test\\+query"

    def test_escape_minus(self):
        assert escape_solr_special_chars("test-query") == "test\\-query"

    def test_escape_exclamation(self):
        assert escape_solr_special_chars("test!query") == "test\\!query"

    def test_escape_parentheses(self):
        assert escape_solr_special_chars("test(query)") == "test\\(query\\)"

    def test_escape_brackets(self):
        assert escape_solr_special_chars("test[query]") == "test\\[query\\]"

    def test_escape_caret(self):
        assert escape_solr_special_chars("test^query") == "test\\^query"

    def test_escape_tilde(self):
        assert escape_solr_special_chars("test~query") == "test\\~query"

    def test_escape_asterisk(self):
        assert escape_solr_special_chars("test*query") == "test\\*query"

    def test_escape_question(self):
        assert escape_solr_special_chars("test?query") == "test\\?query"

    def test_escape_colon(self):
        assert escape_solr_special_chars("test:query") == "test\\:query"

    def test_escape_backslash(self):
        assert escape_solr_special_chars("test\\query") == "test\\\\query"

    def test_escape_multiple(self):
        assert (
            escape_solr_special_chars("test+query-with*special?chars")
            == "test\\+query\\-with\\*special\\?chars"
        )

    def test_no_escape_needed(self):
        assert escape_solr_special_chars("simple query") == "simple query"


class TestSearchDatasetsByTerms:
    """Tests for search_datasets_by_terms function."""

    @pytest.mark.asyncio
    @patch("api.services.datasource_services.search_datasets_by_terms.catalog_settings")
    async def test_search_success_local(self, mock_catalog):
        """Test successful search on local server."""
        mock_repo = MagicMock()
        mock_repo.package_search.return_value = {
            "results": [
                {
                    "id": "dataset-1",
                    "name": "test-dataset",
                    "title": "Test Dataset",
                    "notes": "Test description",
                    "organization": {"name": "test-org"},
                    "extras": [],
                    "resources": [
                        {
                            "id": "res-1",
                            "url": "http://example.com/data.csv",
                            "name": "Data",
                            "description": "Test data",
                            "format": "CSV",
                        }
                    ],
                }
            ]
        }
        mock_catalog.local_catalog = mock_repo

        results = await search_datasets_by_terms(["test"], server="local")

        assert len(results) == 1
        assert results[0].id == "dataset-1"

    @pytest.mark.asyncio
    @patch("api.services.datasource_services.search_datasets_by_terms.catalog_settings")
    async def test_search_success_global(self, mock_catalog):
        """Test successful search on global server."""
        mock_repo = MagicMock()
        mock_repo.package_search.return_value = {
            "results": [
                {
                    "id": "dataset-2",
                    "name": "global-dataset",
                    "title": "Global Dataset",
                    "notes": "Global description",
                    "organization": None,
                    "extras": [],
                    "resources": [],
                }
            ]
        }
        mock_catalog.global_catalog = mock_repo

        results = await search_datasets_by_terms(["global"], server="global")

        assert len(results) == 1

    @pytest.mark.asyncio
    @patch("api.services.datasource_services.search_datasets_by_terms.catalog_settings")
    async def test_search_success_pre_ckan(self, mock_catalog):
        """Test successful search on pre_ckan server."""
        mock_repo = MagicMock()
        mock_repo.package_search.return_value = {"results": []}
        mock_catalog.pre_catalog = mock_repo

        results = await search_datasets_by_terms(["test"], server="pre_ckan")

        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_search_invalid_server(self):
        """Test search with invalid server."""
        with pytest.raises(HTTPException) as exc_info:
            await search_datasets_by_terms(["test"], server="invalid")

        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    @patch("api.services.datasource_services.search_datasets_by_terms.catalog_settings")
    async def test_search_with_keys(self, mock_catalog):
        """Test search with specific keys."""
        mock_repo = MagicMock()
        mock_repo.package_search.return_value = {
            "results": [
                {
                    "id": "dataset-1",
                    "name": "test-dataset",
                    "title": "Test",
                    "organization": None,
                    "extras": [],
                    "resources": [],
                }
            ]
        }
        mock_catalog.local_catalog = mock_repo

        await search_datasets_by_terms(
            ["test", "value"], keys_list=["title", None], server="local"
        )

        mock_repo.package_search.assert_called_once()
        call_args = mock_repo.package_search.call_args
        assert "title:test" in call_args[1]["q"]

    @pytest.mark.asyncio
    @patch("api.services.datasource_services.search_datasets_by_terms.catalog_settings")
    async def test_search_with_null_key(self, mock_catalog):
        """Test search with null key in keys_list."""
        mock_repo = MagicMock()
        mock_repo.package_search.return_value = {"results": []}
        mock_catalog.local_catalog = mock_repo

        await search_datasets_by_terms(["test"], keys_list=["null"], server="local")

        # Should treat "null" as None (global search)
        mock_repo.package_search.assert_called_once()

    @pytest.mark.asyncio
    @patch("api.services.datasource_services.search_datasets_by_terms.catalog_settings")
    async def test_search_not_found(self, mock_catalog):
        """Test search when NotFound is raised."""
        mock_repo = MagicMock()
        mock_repo.package_search.side_effect = NotFound()
        mock_catalog.local_catalog = mock_repo

        results = await search_datasets_by_terms(["test"], server="local")

        assert results == []

    @pytest.mark.asyncio
    @patch("api.services.datasource_services.search_datasets_by_terms.catalog_settings")
    async def test_search_ckan_api_error_local(self, mock_catalog):
        """Test search with CKAN API error on local server."""
        mock_repo = MagicMock()
        mock_repo.package_search.side_effect = CKANAPIError("CKAN error")
        mock_catalog.local_catalog = mock_repo

        with pytest.raises(HTTPException) as exc_info:
            await search_datasets_by_terms(["test"], server="local")

        assert exc_info.value.status_code == 503

    @pytest.mark.asyncio
    @patch("api.services.datasource_services.search_datasets_by_terms.catalog_settings")
    async def test_search_ckan_api_error_global(self, mock_catalog):
        """Test search with CKAN API error on global server."""
        mock_repo = MagicMock()
        mock_repo.package_search.side_effect = CKANAPIError("CKAN error")
        mock_catalog.global_catalog = mock_repo

        with pytest.raises(HTTPException) as exc_info:
            await search_datasets_by_terms(["test"], server="global")

        assert exc_info.value.status_code == 503
        assert "Global" in exc_info.value.detail

    @pytest.mark.asyncio
    @patch("api.services.datasource_services.search_datasets_by_terms.catalog_settings")
    async def test_search_connection_error_local(self, mock_catalog):
        """Test search with connection error on local server."""
        mock_repo = MagicMock()
        mock_repo.package_search.side_effect = requests.exceptions.ConnectionError()
        mock_catalog.local_catalog = mock_repo

        with pytest.raises(HTTPException) as exc_info:
            await search_datasets_by_terms(["test"], server="local")

        assert exc_info.value.status_code == 503
        assert "Local" in exc_info.value.detail

    @pytest.mark.asyncio
    @patch("api.services.datasource_services.search_datasets_by_terms.catalog_settings")
    async def test_search_connection_error_global(self, mock_catalog):
        """Test search with connection error on global server."""
        mock_repo = MagicMock()
        mock_repo.package_search.side_effect = requests.exceptions.ConnectionError()
        mock_catalog.global_catalog = mock_repo

        with pytest.raises(HTTPException) as exc_info:
            await search_datasets_by_terms(["test"], server="global")

        assert exc_info.value.status_code == 503
        assert "Global" in exc_info.value.detail

    @pytest.mark.asyncio
    @patch("api.services.datasource_services.search_datasets_by_terms.catalog_settings")
    async def test_search_connection_error_pre_ckan(self, mock_catalog):
        """Test search with connection error on pre_ckan server."""
        mock_repo = MagicMock()
        mock_repo.package_search.side_effect = requests.exceptions.ConnectionError()
        mock_catalog.pre_catalog = mock_repo

        with pytest.raises(HTTPException) as exc_info:
            await search_datasets_by_terms(["test"], server="pre_ckan")

        assert exc_info.value.status_code == 503
        assert "Pre-CKAN" in exc_info.value.detail

    @pytest.mark.asyncio
    @patch("api.services.datasource_services.search_datasets_by_terms.catalog_settings")
    async def test_search_timeout_error(self, mock_catalog):
        """Test search with timeout error."""
        mock_repo = MagicMock()
        mock_repo.package_search.side_effect = requests.exceptions.Timeout()
        mock_catalog.local_catalog = mock_repo

        with pytest.raises(HTTPException) as exc_info:
            await search_datasets_by_terms(["test"], server="local")

        assert exc_info.value.status_code == 504
        assert "timed out" in exc_info.value.detail

    @pytest.mark.asyncio
    @patch("api.services.datasource_services.search_datasets_by_terms.catalog_settings")
    async def test_search_generic_connection_error_local(self, mock_catalog):
        """Test search with generic connection-related error on local."""
        mock_repo = MagicMock()
        mock_repo.package_search.side_effect = Exception("connection refused")
        mock_catalog.local_catalog = mock_repo

        with pytest.raises(HTTPException) as exc_info:
            await search_datasets_by_terms(["test"], server="local")

        assert exc_info.value.status_code == 503

    @pytest.mark.asyncio
    @patch("api.services.datasource_services.search_datasets_by_terms.catalog_settings")
    async def test_search_generic_connection_error_global(self, mock_catalog):
        """Test search with generic connection-related error on global."""
        mock_repo = MagicMock()
        mock_repo.package_search.side_effect = Exception("max retries exceeded")
        mock_catalog.global_catalog = mock_repo

        with pytest.raises(HTTPException) as exc_info:
            await search_datasets_by_terms(["test"], server="global")

        assert exc_info.value.status_code == 503

    @pytest.mark.asyncio
    @patch("api.services.datasource_services.search_datasets_by_terms.catalog_settings")
    async def test_search_generic_connection_error_pre_ckan(self, mock_catalog):
        """Test search with generic connection-related error on pre_ckan."""
        mock_repo = MagicMock()
        mock_repo.package_search.side_effect = Exception("network unreachable")
        mock_catalog.pre_catalog = mock_repo

        with pytest.raises(HTTPException) as exc_info:
            await search_datasets_by_terms(["test"], server="pre_ckan")

        assert exc_info.value.status_code == 503

    @pytest.mark.asyncio
    @patch("api.services.datasource_services.search_datasets_by_terms.catalog_settings")
    async def test_search_generic_error(self, mock_catalog):
        """Test search with generic non-connection error."""
        mock_repo = MagicMock()
        mock_repo.package_search.side_effect = Exception("Some internal error")
        mock_catalog.local_catalog = mock_repo

        with pytest.raises(HTTPException) as exc_info:
            await search_datasets_by_terms(["test"], server="local")

        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    @patch("api.services.datasource_services.search_datasets_by_terms.catalog_settings")
    async def test_search_with_mapping_extras(self, mock_catalog):
        """Test search results with mapping in extras."""
        mock_repo = MagicMock()
        mock_repo.package_search.return_value = {
            "results": [
                {
                    "id": "dataset-1",
                    "name": "test",
                    "title": "Test",
                    "organization": None,
                    "extras": [{"key": "mapping", "value": '{"field": "value"}'}],
                    "resources": [],
                }
            ]
        }
        mock_catalog.local_catalog = mock_repo

        results = await search_datasets_by_terms(["test"], server="local")

        assert len(results) == 1
        assert results[0].extras["mapping"] == {"field": "value"}

    @pytest.mark.asyncio
    @patch("api.services.datasource_services.search_datasets_by_terms.catalog_settings")
    async def test_search_with_invalid_mapping_json(self, mock_catalog):
        """Test search results with invalid JSON in mapping."""
        mock_repo = MagicMock()
        mock_repo.package_search.return_value = {
            "results": [
                {
                    "id": "dataset-1",
                    "name": "test",
                    "title": "Test",
                    "organization": None,
                    "extras": [{"key": "mapping", "value": "invalid json"}],
                    "resources": [],
                }
            ]
        }
        mock_catalog.local_catalog = mock_repo

        results = await search_datasets_by_terms(["test"], server="local")

        assert len(results) == 1
        assert results[0].extras["mapping"] == "invalid json"

    @pytest.mark.asyncio
    @patch("api.services.datasource_services.search_datasets_by_terms.catalog_settings")
    async def test_search_with_processing_extras(self, mock_catalog):
        """Test search results with processing in extras."""
        mock_repo = MagicMock()
        mock_repo.package_search.return_value = {
            "results": [
                {
                    "id": "dataset-1",
                    "name": "test",
                    "title": "Test",
                    "organization": None,
                    "extras": [{"key": "processing", "value": '{"step": "transform"}'}],
                    "resources": [],
                }
            ]
        }
        mock_catalog.local_catalog = mock_repo

        results = await search_datasets_by_terms(["test"], server="local")

        assert len(results) == 1
        assert results[0].extras["processing"] == {"step": "transform"}

    @pytest.mark.asyncio
    @patch("api.services.datasource_services.search_datasets_by_terms.catalog_settings")
    async def test_search_with_invalid_processing_json(self, mock_catalog):
        """Test search results with invalid JSON in processing."""
        mock_repo = MagicMock()
        mock_repo.package_search.return_value = {
            "results": [
                {
                    "id": "dataset-1",
                    "name": "test",
                    "title": "Test",
                    "organization": None,
                    "extras": [{"key": "processing", "value": "not valid json"}],
                    "resources": [],
                }
            ]
        }
        mock_catalog.local_catalog = mock_repo

        results = await search_datasets_by_terms(["test"], server="local")

        assert len(results) == 1
        assert results[0].extras["processing"] == "not valid json"

    @pytest.mark.asyncio
    @patch("api.services.datasource_services.search_datasets_by_terms.catalog_settings")
    async def test_search_filters_non_matching(self, mock_catalog):
        """Test that results not containing all terms are filtered out."""
        mock_repo = MagicMock()
        mock_repo.package_search.return_value = {
            "results": [
                {
                    "id": "dataset-1",
                    "name": "test",
                    "title": "Test",
                    "notes": "No matching terms here",
                    "organization": None,
                    "extras": [],
                    "resources": [],
                }
            ]
        }
        mock_catalog.local_catalog = mock_repo

        results = await search_datasets_by_terms(["term1", "term2"], server="local")

        assert len(results) == 0
