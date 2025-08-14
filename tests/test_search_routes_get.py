# tests/test_search_routes_get.py
from unittest.mock import patch

import pytest
from fastapi import HTTPException

from api.routes.search_routes.get import search_datasource


class TestSearchDatasourceEndpoint:
    """Test cases for search_datasource endpoint."""

    @patch("api.routes.search_routes.get.datasource_services")
    @pytest.mark.asyncio
    async def test_search_datasource_success_with_all_params(
        self, mock_datasource_services
    ):
        """Test successful search with all parameters provided."""
        # Mock the service response
        mock_results = [
            {
                "id": "dataset1",
                "name": "test_dataset",
                "title": "Test Dataset",
                "organization_id": "org1",
                "owner_org": "test_org",
            },
            {
                "id": "dataset2",
                "name": "another_dataset",
                "title": "Another Dataset",
                "organization_id": "org2",
                "owner_org": "another_org",
            },
        ]
        mock_datasource_services.search_datasource.return_value = mock_results

        # Call the endpoint with all parameters
        result = await search_datasource(
            dataset_name="test_dataset",
            dataset_title="Test Dataset",
            organization_id="org1",
            owner_org="test_org",
            resource_url="http://example.com/data.csv",
            resource_name="test_resource",
            dataset_description="Test description",
            resource_description="Resource description",
            resource_format="CSV",
            search_term="test",
        )

        # Verify the result
        assert result == mock_results

        # Verify the service was called with correct parameters
        mock_datasource_services.search_datasource.assert_called_once_with(
            dataset_name="test_dataset",
            dataset_title="Test Dataset",
            organization_id="org1",
            owner_org="test_org",
            resource_url="http://example.com/data.csv",
            resource_name="test_resource",
            dataset_description="Test description",
            resource_description="Resource description",
            resource_format="CSV",
            search_term="test",
        )

    @patch("api.routes.search_routes.get.datasource_services")
    @pytest.mark.asyncio
    async def test_search_datasource_success_no_params(self, mock_datasource_services):
        """Test successful search with no parameters (all None)."""
        mock_results = []
        mock_datasource_services.search_datasource.return_value = mock_results

        result = await search_datasource()

        assert result == mock_results

        # Verify the service was called once (FastAPI passes Query objects, not None directly)
        mock_datasource_services.search_datasource.assert_called_once()

    @patch("api.routes.search_routes.get.datasource_services")
    @pytest.mark.asyncio
    async def test_search_datasource_partial_params(self, mock_datasource_services):
        """Test successful search with only some parameters provided."""
        mock_results = [{"id": "dataset1", "name": "found_dataset"}]
        mock_datasource_services.search_datasource.return_value = mock_results

        result = await search_datasource(
            dataset_name="test_dataset", search_term="test"
        )

        assert result == mock_results

        # Verify the service was called with provided params (FastAPI handles defaults)
        mock_datasource_services.search_datasource.assert_called_once()
        call_kwargs = mock_datasource_services.search_datasource.call_args.kwargs
        assert call_kwargs["dataset_name"] == "test_dataset"
        assert call_kwargs["search_term"] == "test"

    @patch("api.routes.search_routes.get.datasource_services")
    @pytest.mark.asyncio
    async def test_search_datasource_empty_results(self, mock_datasource_services):
        """Test search that returns empty results."""
        mock_datasource_services.search_datasource.return_value = []

        result = await search_datasource(search_term="nonexistent")

        assert result == []
        mock_datasource_services.search_datasource.assert_called_once()

    @patch("api.routes.search_routes.get.datasource_services")
    @pytest.mark.asyncio
    async def test_search_datasource_service_exception(self, mock_datasource_services):
        """Test handling of service exceptions."""
        # Mock service to raise an exception
        mock_datasource_services.search_datasource.side_effect = Exception(
            "Database connection error"
        )

        # Verify HTTPException is raised
        with pytest.raises(HTTPException) as exc_info:
            await search_datasource(search_term="test")

        assert exc_info.value.status_code == 400
        assert "Database connection error" in str(exc_info.value.detail)
        mock_datasource_services.search_datasource.assert_called_once()

    @patch("api.routes.search_routes.get.datasource_services")
    @pytest.mark.asyncio
    async def test_search_datasource_generic_exception(self, mock_datasource_services):
        """Test handling of generic exceptions."""
        mock_datasource_services.search_datasource.side_effect = ValueError(
            "Invalid search parameters"
        )

        with pytest.raises(HTTPException) as exc_info:
            await search_datasource(dataset_name="invalid")

        assert exc_info.value.status_code == 400
        assert "Invalid search parameters" in str(exc_info.value.detail)

    @patch("api.routes.search_routes.get.datasource_services")
    @pytest.mark.asyncio
    async def test_search_datasource_with_special_characters(
        self, mock_datasource_services
    ):
        """Test search with special characters in parameters."""
        mock_results = [{"id": "dataset1"}]
        mock_datasource_services.search_datasource.return_value = mock_results

        result = await search_datasource(
            dataset_name="test-dataset_v1.0", search_term="test@example.com"
        )

        assert result == mock_results
        mock_datasource_services.search_datasource.assert_called_once()
        call_kwargs = mock_datasource_services.search_datasource.call_args.kwargs
        assert call_kwargs["dataset_name"] == "test-dataset_v1.0"
        assert call_kwargs["search_term"] == "test@example.com"

    @patch("api.routes.search_routes.get.datasource_services")
    @pytest.mark.asyncio
    async def test_search_datasource_with_empty_strings(self, mock_datasource_services):
        """Test search with empty string parameters."""
        mock_results = []
        mock_datasource_services.search_datasource.return_value = mock_results

        result = await search_datasource(dataset_name="", search_term="")

        assert result == mock_results
        mock_datasource_services.search_datasource.assert_called_once()
        call_kwargs = mock_datasource_services.search_datasource.call_args.kwargs
        assert call_kwargs["dataset_name"] == ""
        assert call_kwargs["search_term"] == ""
